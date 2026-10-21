import assert from "node:assert/strict";
import test from "node:test";
import { spawnSync } from "node:child_process";
import {
  mkdtempSync,
  readFileSync,
  readdirSync,
  rmSync,
  statSync,
  writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { MemoryOutbox } from "../dist/outbox.js";

function directory(t) {
  const path = mkdtempSync(join(tmpdir(), "reme-outbox-"));
  t.after(() => rmSync(path, { recursive: true, force: true }));
  return path;
}

const messages = [
  {
    id: "m1",
    name: "user",
    role: "user",
    content: [{ type: "text", text: "private fact" }],
  },
];

test("recovers a partial batch after the owning process exits without cleanup", (t) => {
  const path = directory(t);
  const child = spawnSync(
    process.execPath,
    [
      "--input-type=module",
      "--eval",
      `
    import { MemoryOutbox } from ${JSON.stringify(
      new URL("../dist/outbox.js", import.meta.url).href,
    )};
    const queue = new MemoryOutbox(${JSON.stringify(path)});
    queue.append("http://localhost:2333", "session", "2026-10-21", ${JSON.stringify(
      messages,
    )}, 5);
  `,
    ],
    { encoding: "utf8" },
  );
  assert.equal(child.status, 0, child.stderr);
  const recovered = new MemoryOutbox(path);
  try {
    recovered.flush();
    assert.deepEqual(recovered.stats(), { turns: 1, batches: 1 });
    const { name, batch } = recovered.next();
    assert.deepEqual(batch.turns, [messages]);
    if (process.platform !== "win32")
      assert.equal(statSync(join(path, name)).mode & 0o777, 0o600);
    recovered.acknowledge(name);
    assert.deepEqual(recovered.stats(), { turns: 0, batches: 0 });
  } finally {
    recovered.close();
  }
});

test("refuses another owner without changing the queue", (t) => {
  const path = directory(t);
  const queue = new MemoryOutbox(path);
  try {
    queue.append("http://localhost:2333", "session", "2026-10-21", messages, 1);
    assert.throws(() => new MemoryOutbox(path), /in use/);
    assert.equal(queue.stats().turns, 1);
  } finally {
    queue.close();
  }
});

test("preserves invalid records and keeps parser errors free of message content", (t) => {
  const path = directory(t);
  const queue = new MemoryOutbox(path);
  try {
    queue.append("http://localhost:2333", "session", "2026-10-21", messages, 1);
    const name = readdirSync(path).find((file) => file.startsWith("ready-"));
    const stored = JSON.parse(readFileSync(join(path, name), "utf8"));
    stored.id = "../outside";
    writeFileSync(join(path, name), JSON.stringify(stored));
    assert.throws(() => queue.next(), /Invalid ReMe outbox record/);
    writeFileSync(join(path, name), "PRIVATE-CONTENT");
    assert.throws(
      () => queue.next(),
      (error) => !error.message.includes("PRIVATE-CONTENT"),
    );
    assert.equal(readFileSync(join(path, name), "utf8"), "PRIVATE-CONTENT");
  } finally {
    queue.close();
  }
});
