---
new: true
---
# Memory Library

<div id="memory-lib-root" class="ml-prose-container">
  <!-- 工具条 -->
  <div class="ml-card">
    <div class="ml-toolbar">
      <div class="ml-input-wrap">
        <svg class="ml-icon" viewBox="0 0 24 24" aria-hidden="true">
          <path d="M15.5 14h-.79l-.28-.27A6.471 6.471 0 0 0 16 9.5 6.5 6.5 0 1 0 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"/>
        </svg>
        <input id="ml-search" placeholder="Search libraries or memories..." />
      </div>
      <button id="ml-clear" class="ml-btn secondary">Clear</button>
    </div>
    <div id="ml-stats" class="ml-stats" hidden>
      <span>Showing <b id="ml-count">0</b> of <b id="ml-total">0</b> <span id="ml-type">items</span></span>
    </div>
  </div>

  <!-- 加载/错误 -->
  <div id="ml-loading" class="ml-loading">
    <div class="ml-spinner" aria-label="Loading"></div>
    <div class="ml-muted">Loading memory library…</div>
  </div>
  <div id="ml-error" class="ml-error" hidden>
    <div class="ml-error-icon">⚠️</div>
    <div class="ml-muted">Failed to load memory library.</div>
    <button id="ml-retry" class="ml-btn">Try again</button>
  </div>

  <!-- 面包屑 -->
  <div id="ml-crumb" class="ml-crumb" hidden>
    <button id="ml-back" class="ml-link">← Back to Libraries</button>
    <div class="ml-crumb-title" id="ml-crumb-title">Libraries</div>
  </div>

  <!-- 列表容器 -->
  <div id="ml-libraries" class="ml-stacked" hidden></div>

  <div id="ml-memories" class="ml-grid" hidden></div>
  <div id="ml-pagination" class="ml-pagination" hidden>
    <div class="ml-page-info">
      <span id="ml-page-range"></span>
    </div>
    <div class="ml-page-controls">
      <button id="ml-prev" class="ml-btn secondary">← Prev</button>
      <button id="ml-next" class="ml-btn">Next →</button>
    </div>
  </div>

  <!-- 空态 -->
  <div id="ml-empty" class="ml-empty" hidden>
    <div class="ml-empty-icon">🔎</div>
    <div class="ml-muted">No results found. Try changing your search.</div>
  </div>
</div>

<!-- 详情弹窗 -->
<dialog id="ml-modal" class="ml-modal">
  <form method="dialog" class="ml-modal-card">
    <div class="ml-modal-header">
      <div>
        <div class="ml-chip" id="ml-modal-lib"></div>
        <div class="ml-chip success" id="ml-modal-score" hidden></div>
      </div>
      <button class="ml-close" aria-label="Close">✕</button>
    </div>

    <div class="ml-modal-section">
      <div class="ml-section-title">When to use</div>
      <div class="ml-code" id="ml-modal-when"></div>
    </div>

    <div class="ml-modal-section">
      <div class="ml-section-title">Memory</div>
      <div class="ml-note" id="ml-modal-content"></div>
    </div>

    <div class="ml-modal-section">
      <div class="ml-section-title">Metadata</div>
      <div class="ml-meta">
        <div><span>Author</span><b id="ml-modal-author"></b></div>
        <div><span>Created</span><b id="ml-modal-created"></b></div>
        <div><span>Memory ID</span><b id="ml-modal-id" class="mono"></b></div>
        <div><span>Workspace</span><b id="ml-modal-ws" class="mono"></b></div>
      </div>
    </div>

    <div class="ml-modal-footer">
      <button class="ml-btn secondary" value="cancel">Close</button>
    </div>
  </form>
</dialog>

<style>
:root {
  --ml-radius: .75rem;
  --ml-gap: 1rem;
  --ml-shadow: 0 6px 24px rgba(0,0,0,.08);
}
.ml-prose-container { display: grid; gap: var(--ml-gap); }
.ml-card {
  background: var(--background, #fff);
  color: var(--foreground, #0a0a0a);
  border: 1px solid var(--border, rgba(0,0,0,.08));
  border-radius: var(--ml-radius);
  padding: 1rem;
  box-shadow: var(--shadow, 0 1px 0 rgba(0,0,0,.02));
}

/* general card/grid */
.ml-grid {
  display: grid;
  gap: var(--ml-gap);
  grid-template-columns: repeat(1, minmax(0,1fr));
}
@media (min-width: 640px){ .ml-grid{ grid-template-columns: repeat(2, minmax(0,1fr)); } }
@media (min-width: 1024px){ .ml-grid{ grid-template-columns: repeat(3, minmax(0,1fr)); } }

/* libraries stacked (categories vertical, libraries 1 per row) */
.ml-stacked { display: grid; gap: 1.25rem; }
.ml-section{ display:grid; gap:.5rem; }
.ml-section h3{ margin:.25rem 0; font-size:1.05rem; font-weight:700; opacity:.85; display:flex; gap:.5rem; align-items:center; }

.ml-card-item{
  background: var(--card, var(--background, #fff));
  border: 1px solid var(--border, rgba(0,0,0,.08));
  border-radius: var(--ml-radius);
  padding: 1rem;
  transition: transform .18s ease, box-shadow .18s ease, border-color .18s ease;
  cursor: pointer;
}
.ml-card-item:hover{
  transform: translateY(-2px);
  box-shadow: var(--ml-shadow);
  border-color: var(--primary, #3b82f6);
}
.ml-card-head{ display:flex; align-items:flex-start; justify-content:space-between; gap:.75rem; margin-bottom:.5rem; }
.ml-card-title{ font-weight: 650; font-size: 1rem; }
.ml-card-sub{ font-size: .85rem; opacity: .7; }
.ml-card-sample{ margin-top:.5rem; font-size:.92rem; line-height:1.5; opacity:.9; display:-webkit-box; -webkit-line-clamp:3; -webkit-box-orient:vertical; overflow:hidden; }
.ml-card-foot{ display:flex; justify-content:space-between; align-items:center; border-top:1px solid var(--border, rgba(0,0,0,.08)); padding-top:.5rem; margin-top:.75rem; font-size:.85rem; opacity:.8; }

/* toolbar */
.ml-toolbar{ display:flex; gap:.75rem; align-items:center; justify-content:space-between; flex-wrap:wrap; }
.ml-input-wrap{ position:relative; flex:1; min-width: 260px; }
.ml-input-wrap input{
  width:100%; padding:.6rem .9rem .6rem 2.2rem; border-radius:.6rem;
  border:1px solid var(--border, rgba(0,0,0,.12));
  background: var(--muted, rgba(0,0,0,.02));
  color: var(--foreground, #0a0a0a);
  outline:none;
}
.ml-input-wrap input:focus{
  border-color: var(--primary, #3b82f6);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--primary, #3b82f6) 22%, transparent);
  background: var(--background, #fff);
}
.ml-icon{ position:absolute; left:.6rem; top:50%; transform:translateY(-50%); width:1.1rem; height:1.1rem; opacity:.6; }

.ml-btn{
  border:1px solid var(--border, rgba(0,0,0,.12));
  background: var(--accent, var(--background, #fff));
  color: var(--foreground, #0a0a0a);
  padding:.55rem .9rem; border-radius:.55rem; cursor:pointer;
}
.ml-btn.secondary{ background: var(--muted, rgba(0,0,0,.03)); }
.ml-btn:hover{ border-color: var(--primary, #3b82f6); }

/* stats/breadcrumb */
.ml-stats{ margin-top:.5rem; font-size:.9rem; opacity:.8; }
.ml-crumb{ display:flex; align-items:center; gap:.75rem; }
.ml-link{ background:none; border:none; color: var(--primary, #3b82f6); cursor:pointer; padding:.25rem .5rem; border-radius:.4rem; }
.ml-link:hover{ text-decoration: underline; }
.ml-crumb-title{ font-weight:600; opacity:.8; }

/* states */
.ml-loading, .ml-error, .ml-empty{ display:grid; justify-items:center; gap:.5rem; padding:3rem 1rem; }
.ml-spinner{
  width:38px; height:38px; border-radius:999px; border:3px solid color-mix(in srgb, var(--foreground,#000) 12%, transparent);
  border-top-color: var(--primary,#3b82f6); animation: ml-spin 1s linear infinite;
}
@keyframes ml-spin{ to{ transform: rotate(360deg); } }
.ml-muted{ opacity:.7; }
.ml-error-icon{ font-size:1.4rem; }

/* chips */
.ml-chip{ display:inline-block; padding:.25rem .55rem; border-radius:999px; font-size:.78rem;
  background: color-mix(in srgb, var(--primary,#3b82f6) 12%, transparent); color: var(--primary,#3b82f6);
}
.ml-chip.success{
  background: color-mix(in srgb, #16a34a 14%, transparent);
  color: #16a34a;
}
.ml-chip.beta{
  background: color-mix(in srgb, #f59e0b 14%, transparent);
  color: #b45309;
}

/* code/note */
.ml-code{
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
  background: var(--muted, rgba(0,0,0,.04)); border:1px solid var(--border, rgba(0,0,0,.08));
  padding:.75rem; border-radius:.6rem; white-space:pre-wrap;
}
.ml-note{
  background: color-mix(in srgb, #f59e0b 9%, transparent);
  border:1px solid color-mix(in srgb, #f59e0b 28%, transparent);
  padding:.75rem; border-radius:.6rem;
}

/* meta */
.ml-meta{ display:grid; grid-template-columns: repeat(1, minmax(0,1fr)); gap:.5rem; }
@media (min-width: 640px){ .ml-meta{ grid-template-columns: repeat(2, minmax(0,1fr)); } }
.ml-meta > div{ display:flex; justify-content:space-between; align-items:center; padding:.5rem .75rem;
  border:1px dashed var(--border, rgba(0,0,0,.12)); border-radius:.5rem; background: var(--background, #fff);
}
.ml-meta span{ opacity:.7; }
.mono{ font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; }

/* modal */
.ml-modal{ padding:0; border:none; background: transparent; }
.ml-modal[open]{ display:grid; align-items:center; justify-items:center; }
.ml-modal::backdrop{ background: rgba(0,0,0,.45); }
.ml-modal-card{
  width:min(100%, 960px); max-height: 85vh; overflow:auto;
  background: var(--background, #fff); color: var(--foreground,#0a0a0a);
  border:1px solid var(--border, rgba(0,0,0,.1)); border-radius: var(--ml-radius);
  padding: 1rem; box-shadow: var(--ml-shadow);
}
.ml-modal-header{ display:flex; justify-content:space-between; align-items:center; gap:.75rem; margin-bottom:.5rem; }
.ml-close{ border:none; background:none; font-size:1.1rem; cursor:pointer; opacity:.6; }
.ml-close:hover{ opacity:1; }
.ml-modal-section{ display:grid; gap:.35rem; margin-top:.75rem; }
.ml-section-title{ font-weight:650; opacity:.85; }
.ml-modal-footer{ display:flex; justify-content:flex-end; margin-top:1rem; }

/* pagination */
.ml-pagination{
  display:flex; justify-content:space-between; align-items:center;
  padding:.5rem .25rem;
}
.ml-page-controls{ display:flex; gap:.5rem; }
.ml-page-info{ font-size:.9rem; opacity:.8; }
</style>

<script>
(() => {
  // —— State
  let ALL = [];
  let GROUPED = {};
  let VIEW = "libraries"; // "libraries" | "memories"
  let CURR = null;

  // pagination state for memories
  let PAGE = 1;
  const PAGE_SIZE = 30;
  let CURRENT_MEM_LIST = [];

  // —— DOM
  const $ = (id) => document.getElementById(id);
  const elLoading = $("ml-loading");
  const elError = $("ml-error");
  const elRetry = $("ml-retry");
  const elLibraries = $("ml-libraries");
  const elMemories = $("ml-memories");
  const elPagination = $("ml-pagination");
  const elPageRange = $("ml-page-range");
  const elPrev = $("ml-prev");
  const elNext = $("ml-next");
  const elEmpty = $("ml-empty");
  const elSearch = $("ml-search");
  const elClear = $("ml-clear");
  const elStats = $("ml-stats");
  const elCount = $("ml-count");
  const elTotal = $("ml-total");
  const elType = $("ml-type");
  const elCrumb = $("ml-crumb");
  const elBack = $("ml-back");
  const elCrumbTitle = $("ml-crumb-title");
  const dlg = $("ml-modal");

  const mLib = $("ml-modal-lib");
  const mScore = $("ml-modal-score");
  const mWhen = $("ml-modal-when");
  const mCont = $("ml-modal-content");
  const mAuth = $("ml-modal-author");
  const mCreated = $("ml-modal-created");
  const mId = $("ml-modal-id");
  const mWs = $("ml-modal-ws");

  // —— Config：JSONL 文件位于本页同级目录（docs/library/）
  const BASE = "..";
  const FILES = [
    "appworld.jsonl",
    "bfcl_v3.jsonl",
    "research_plan.jsonl",
    "research_tips.jsonl",
    // 需要的话在这里继续添加文件名
  ];

  // —— Categories
  const CATEGORY_MAP = {
    "Academic Datasets": ["appworld", "bfcl_v3"],
    "Finance": ["research_plan", "research_tips"],
    "Medical": [] // header only if empty
  };

  // —— Utils
  function show(el){ el.hidden = false; }
  function hide(el){ el.hidden = true; }
  function setLoading(on){
    on ? (show(elLoading), [elError, elLibraries, elMemories, elEmpty, elStats, elCrumb, elPagination].forEach(hide))
       : hide(elLoading);
  }
  function setError(on){ on ? (show(elError), [elLoading].forEach(hide)) : hide(elError); }
  function clampTxt(s, n){ if(!s) return ""; return s.length<=n? s : s.slice(0,n)+"…"; }
  const fmtDate = (t)=> t ? new Date(t).toLocaleDateString() : "Unknown";
  function debounce(fn, ms=250){ let t; return (...a)=>{ clearTimeout(t); t=setTimeout(()=>fn(...a), ms); }; }
  function fileBase(name){ return name.replace(/\.jsonl$/,""); }

  // —— Data Loading
  async function loadAll(){
    setLoading(true); setError(false);
    try{
      const arr = await Promise.all(FILES.map(async f=>{
        try{
          const res = await fetch(`${BASE}/${f}`);
          if(!res.ok) return [];
          const txt = await res.text();
          return txt.split("\n").filter(l=>l.trim()).map(line=>{
            try{
              const obj = JSON.parse(line);
              obj._library = fileBase(f);
              return obj;
            }catch{ return null; }
          }).filter(Boolean);
        }catch{ return []; }
      }));
      ALL = arr.flat();
      if(!ALL.length) throw new Error("no data");
      GROUPED = ALL.reduce((acc,m)=>{
        (acc[m._library] ||= []).push(m);
        return acc;
      }, {});
      renderLibraries();
    }catch(e){
      setError(true);
    }finally{
      setLoading(false);
    }
  }

  // —— Render — Libraries (stacked categories; libs 1 per row)
  function renderLibraries(){
    VIEW = "libraries"; CURR = null;
    PAGE = 1; CURRENT_MEM_LIST = [];
    hide(elMemories); hide(elEmpty); hide(elPagination); show(elLibraries);
    hide(elCrumb);
    elCrumbTitle.textContent = "Libraries";
    elType.textContent = "libraries";

    const availableLibs = Object.keys(GROUPED);

    const sections = Object.entries(CATEGORY_MAP).map(([cat, prefixes])=>{
      // build libraries list for this category
      const libs = (prefixes || []).filter(p => availableLibs.includes(p));
      const itemsHtml = libs.map(name=>{
        const arr = GROUPED[name];
        const sample = arr[0] || {};
        const sampleText = sample.when_to_use || sample.content || "No description available";
        const author = sample.author || "Unknown";
        return `
          <div class="ml-card-item" data-lib="${name}">
            <div class="ml-card-head">
              <div>
                <div class="ml-card-title">${name}</div>
                <div class="ml-card-sub">${arr.length} memories</div>
              </div>
              <div class="ml-chip">DB</div>
            </div>
            <div class="ml-card-sample">${clampTxt(sampleText, 180)}</div>
            <div class="ml-card-foot">
              <span>👤 ${author}</span>
              <span>View →</span>
            </div>
          </div>
        `;
      }).join("");

      // Category header with Finance (beta) chip
      const betaChip = (cat === "Finance") ? `<span class="ml-chip beta">beta</span>` : "";

      return `
        <section class="ml-section">
          <h3>${cat} ${betaChip}</h3>
          <div class="ml-grid">
            ${itemsHtml}
          </div>
        </section>
      `;
    }).join("");

    elLibraries.innerHTML = sections;

    bindLibraryClicks();

    show(elStats);
    const catsShown = Object.keys(CATEGORY_MAP).length;
    $("ml-count").textContent = catsShown;
    $("ml-total").textContent = catsShown;
  }

  // —— Render — Memories with Pagination
  function renderMemories(memList){
    VIEW = "memories";
    hide(elLibraries); hide(elEmpty); show(elMemories);
    show(elCrumb);
    elType.textContent = "memories";
    elCrumbTitle.textContent = `Exploring ${CURR}`;

    CURRENT_MEM_LIST = memList || [];
    if(!CURRENT_MEM_LIST.length){
      hide(elMemories); hide(elPagination); show(elEmpty); hide(elStats); return;
    }

    const total = CURRENT_MEM_LIST.length;
    const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));
    if(PAGE > pages) PAGE = pages;

    const startIdx = (PAGE - 1) * PAGE_SIZE;
    const endIdx = Math.min(startIdx + PAGE_SIZE, total);
    const pageItems = CURRENT_MEM_LIST.slice(startIdx, endIdx);

    elMemories.innerHTML = pageItems.map((m,idxOnPage)=>`
      <div class="ml-card-item" data-idx="${startIdx + idxOnPage}">
        <div class="ml-card-head">
          <div class="ml-chip">${m._library}</div>
          ${("score" in m && m.score !== null && m.score !== undefined) ? `<div class="ml-chip success">Score: ${m.score}</div>` : ""}
        </div>
        <div class="ml-card-sample"><b>When to use:</b> ${clampTxt(m.when_to_use || "No specific guidance provided", 140)}</div>
        <div class="ml-card-foot">
          <span>👤 ${m.author || "Unknown"}</span>
          <span>Details →</span>
        </div>
      </div>
    `).join("");

    // modal binding
    [...elMemories.querySelectorAll(".ml-card-item")].forEach(card=>{
      card.addEventListener("click", ()=>{
        const absIdx = Number(card.getAttribute("data-idx"));
        const m = CURRENT_MEM_LIST[absIdx];
        mLib.textContent = m._library;
        const hasScore = "score" in m && m.score !== null && m.score !== undefined;
        if(hasScore){ mScore.textContent = `Score: ${m.score}`; mScore.hidden = false; } else { mScore.hidden = true; }
        mWhen.textContent = m.when_to_use || "No specific guidance provided";
        mCont.textContent = m.content || "No content available";
        mAuth.textContent = m.author || "Unknown";
        mCreated.textContent = fmtDate(m.time_created);
        mId.textContent = m.memory_id || "N/A";
        mWs.textContent = m.workspace_id || "N/A";
        dlg.showModal();
      });
    });

    // pagination controls
    show(elPagination);
    elPageRange.textContent = `Showing ${startIdx + 1}–${endIdx} of ${total}`;
    elPrev.disabled = PAGE <= 1;
    elNext.disabled = PAGE >= pages;

    elPrev.onclick = ()=>{ if(PAGE > 1){ PAGE--; renderMemories(CURRENT_MEM_LIST); } };
    elNext.onclick = ()=>{ if(PAGE < pages){ PAGE++; renderMemories(CURRENT_MEM_LIST); } };

    show(elStats);
    elCount.textContent = pageItems.length;
    elTotal.textContent = total;
  }

  function bindLibraryClicks(){
    [...elLibraries.querySelectorAll(".ml-card-item[data-lib]")].forEach(card=>{
      card.addEventListener("click", ()=>{
        CURR = card.getAttribute("data-lib");
        PAGE = 1;
        renderMemories(GROUPED[CURR]);
      });
    });
  }

  // —— Search
  function handleSearch(){
    const q = elSearch.value.trim().toLowerCase();
    if(!q){
      if(VIEW==="libraries") renderLibraries();
      else { PAGE = 1; renderMemories(GROUPED[CURR]); }
      return;
    }
    if(VIEW==="libraries"){
      // filter categories if name matches, or any of their libs/memories match
      const availableLibs = Object.keys(GROUPED);
      const filteredEntries = Object.entries(CATEGORY_MAP).filter(([cat, prefixes])=>{
        if(cat.toLowerCase().includes(q)) return true;
        return (prefixes || []).some(name=>{
          if(!availableLibs.includes(name)) return false;
          const arr = GROUPED[name] || [];
          if(name.toLowerCase().includes(q)) return true;
          return arr.some(m =>
            (m.when_to_use||"").toLowerCase().includes(q) ||
            (m.content||"").toLowerCase().includes(q) ||
            (m.author||"").toLowerCase().includes(q)
          );
        });
      });
      const tmp = Object.fromEntries(filteredEntries);
      const backup = {...CATEGORY_MAP};
      Object.keys(CATEGORY_MAP).forEach(k=> delete CATEGORY_MAP[k]);
      Object.assign(CATEGORY_MAP, tmp);
      renderLibraries();
      Object.keys(CATEGORY_MAP).forEach(k=> delete CATEGORY_MAP[k]);
      Object.assign(CATEGORY_MAP, backup);
    }else{
      const arr = GROUPED[CURR] || [];
      const filtered = arr.filter(m =>
        (m.when_to_use||"").toLowerCase().includes(q) ||
        (m.content||"").toLowerCase().includes(q) ||
        (m.author||"").toLowerCase().includes(q)
      );
      PAGE = 1;
      renderMemories(filtered);
    }
  }

  // —— Events
  elRetry?.addEventListener("click", loadAll);
  elBack?.addEventListener("click", ()=> renderLibraries());
  elSearch?.addEventListener("input", debounce(handleSearch, 250));
  elClear?.addEventListener("click", ()=>{
    elSearch.value = ""; handleSearch();
  });

  // —— Init
  document.addEventListener("DOMContentLoaded", loadAll);
})();
</script>