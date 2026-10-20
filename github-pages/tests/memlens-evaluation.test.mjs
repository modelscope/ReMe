import assert from "node:assert/strict";
import { access, readFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const siteDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const generatedDir = path.join(siteDir, ".generated/site");
const docsDir = path.resolve(siteDir, "../docs");
const methods = ["Full Context Image", "ReMe Text", "ReMe Image", "OpenViking", "Mem0"];
// Published binary verdict counts, not raw benchmark outputs or a second chart generator.
const models = [
  { name: "Qwen3.6-35B-A3B", figure: "qwen36", correct: [89, 78, 101, 70, 73] },
  { name: "Qwen3.8-Max", figure: "qwen38", correct: [124, 100, 137, 80, 97] },
];
const excluded = ["q_028cb832", "q_1d99a36c", "q_3b01c02a", "q_564a657b", "q_600a79aa", "q_c9f8e24d"];
const publicRevision = "f89f166dcf8b5b37a4ed9a5e7c3fdbdd042170d8";
const reproductionRevision = "d3e79918622173306be79ecda6494acadc7c4312";

test("MemLens notes, chart geometry and bilingual blog values agree", async () => {
  for (const language of ["en", "zh"]) {
    const blog = await readFile(path.join(generatedDir, language, "blog_20261009.md"), "utf8");
    const notes = await readFile(path.join(generatedDir, language, "memlens_256k_evaluation.md"), "utf8");
    const rows = notes.split("\n").filter((line) => /^\| Qwen.*\| \d+ \/ 189 \|/.test(line));
    assert.equal(rows.length, 10);
    for (const model of models) {
      const svg = await readFile(path.join(docsDir, "figure", `memlens-256k-${model.figure}-judge.svg`), "utf8");
      const bars = [...svg.matchAll(/<g data-method="([^"]+)" data-score="([\d.]+)">\s*<rect[^>]*y="([\d.]+)"[^>]*height="([\d.]+)"/g)];
      assert.equal(bars.length, 5);
      for (const [index, method] of methods.entries()) {
        const correct = model.correct[index];
        const score = (100 * correct / 189).toFixed(2);
        assert.ok(rows.includes(`| ${model.name} | ${method} | ${correct} / 189 | ${score} |`));
        assert.ok(blog.includes(`${method} ${score}%`), `${language}: alt text for ${model.name}/${method}`);
        assert.equal(bars[index][1], method);
        assert.equal(bars[index][2], score);
        assert.ok(Math.abs(Number(bars[index][4]) - Number(score) * 3) < 0.001);
        assert.ok(Math.abs(Number(bars[index][3]) + Number(bars[index][4]) - 416) < 0.001);
      }
      const gain = (100 * (model.correct[2] - model.correct[0]) / 189).toFixed(2);
      assert.ok(blog.includes(`**${gain}**`));
      assert.ok(notes.includes(`**${gain}**`));
    }
  }
});

test("MemLens notes identify each moderation case and separate paired results", async () => {
  const triggers = {
    zh: [
      ["OpenViking / Max", "记忆构建"],
      ["OpenViking / A3B", "记忆构建"],
      ["ReMe Text、Image / A3B；OpenViking / A3B、Max；Mem0 / A3B", "记忆构建"],
      ["ReMe Image / Max", "回答"],
      ["ReMe Image / Max", "记忆构建"],
      ["ReMe Text / Max", "回答"],
    ],
    en: [
      ["OpenViking / Max", "Memory construction"],
      ["OpenViking / A3B", "Memory construction"],
      ["ReMe Text and Image / A3B; OpenViking / A3B and Max; Mem0 / A3B", "Memory construction"],
      ["ReMe Image / Max", "Answering"],
      ["ReMe Image / Max", "Memory construction"],
      ["ReMe Text / Max", "Answering"],
    ],
  };
  for (const language of ["en", "zh"]) {
    const notes = await readFile(path.join(generatedDir, language, "memlens_256k_evaluation.md"), "utf8");
    const filter = notes.split("{#content-moderation-filter}")[1].split("{#independent-reproduction}")[0];
    assert.deepEqual([...new Set(filter.match(/q_[0-9a-f]{8}/g))].sort(), excluded);
    const rows = filter.split("\n").filter((line) => line.startsWith("| `q_"));
    assert.deepEqual(rows, excluded.map((id, index) => {
      const [method, stage] = triggers[language][index];
      return `| \`${id}\` | ${method} | ${stage} |`;
    }));
    assert.match(filter, /189\/195/);
    assert.ok(notes.includes("| Qwen3.6-35B-A3B | 188 | 100 | 96 | 53.19 → 51.06 |"));
    assert.ok(notes.includes("| Qwen3.8-Max | 187 | 135 | 134 | 72.19 → 71.66 |"));
    assert.match(notes, /temperature 0|temperature \*\*0\*\*/);
    assert.match(notes, /256/);
    assert.match(notes, /memory-only|restricted to memory|限定为 memory/);
  }
});

test("MemLens notes pin the reproduction revision and public links without private audit details", async () => {
  for (const language of ["en", "zh"]) {
    const blog = await readFile(path.join(generatedDir, language, "blog_20261009.md"), "utf8");
    const notesPath = path.join(generatedDir, language, "memlens_256k_evaluation.md");
    await access(notesPath);
    const notes = await readFile(notesPath, "utf8");
    assert.match(blog, /\]\(\.\/memlens_256k_evaluation\.md\)/);
    assert.match(notes, /\]\(\.\/blog_20261009\.md#memlens-256k-results\)/);
    const links = [...notes.matchAll(/\]\((https:\/\/github\.com\/wang-qisen\/ReMe\/blob\/[^)]+)\)/g)];
    assert.equal(links.length, 4);
    for (const [, link] of links) assert.ok(link.includes(`/blob/${publicRevision}/`));
    assert.doesNotMatch(notes, /\/mnt\/|\/Users\/|docs\/_build|file:\/\//);
    const reproduction = notes.split("{#independent-reproduction}")[1];
    assert.ok(reproduction.includes(`\`${reproductionRevision}\``));
    const prose = notes.replace(/\]\([^)]+\)/g, "]").replace(reproductionRevision, "");
    assert.doesNotMatch(prose, /\b[a-f0-9]{40,64}\b/);
    for (const anchor of ["results", "evaluation-settings", "content-moderation-filter", "independent-reproduction"]) {
      assert.ok(notes.includes(`{#${anchor}}`));
    }
  }
});
