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

  const THIS_SCRIPT = document.currentScript || (() => {
      const scripts = document.getElementsByTagName('script');
      return scripts[scripts.length - 1];
    })();

    const SCRIPT_DIR = new URL('./', THIS_SCRIPT.src);
    const DATA_BASE = new URL('./data/', SCRIPT_DIR).href;

  // —— Categories
  const CATEGORY_MAP = {
    "Academic Datasets": ["appworld", "bfcl_v3"],
    "Finance": ["research_plan", "research_tips"],
    "Medical/Law/Education": [] // header only if empty
  };

  const FILES = Array.from(new Set(
    Object.values(CATEGORY_MAP).flat().map(n => `${n}.jsonl`)
  ));

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
          const res = await fetch(new URL(f, DATA_BASE));
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

  function createMemoryModal() {
  // 外层 <dialog>
  const dlg = document.createElement('dialog');
  dlg.id = 'ml-modal';
  dlg.className = 'ml-modal';
  dlg.innerHTML = `
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
  `;
  document.body.appendChild(dlg);

  // 缓存内部节点（创建后一定存在，不会为 null）
  const els = {
    lib: dlg.querySelector('#ml-modal-lib'),
    score: dlg.querySelector('#ml-modal-score'),
    when: dlg.querySelector('#ml-modal-when'),
    content: dlg.querySelector('#ml-modal-content'),
    author: dlg.querySelector('#ml-modal-author'),
    created: dlg.querySelector('#ml-modal-created'),
    id: dlg.querySelector('#ml-modal-id'),
    ws: dlg.querySelector('#ml-modal-ws'),
    closeBtn: dlg.querySelector('.ml-close'),
    card: dlg.querySelector('.ml-modal-card')
  };

  // —— 打开/关闭（含退化）
  function openDialog() {
    try {
      if (typeof dlg.showModal === 'function') {
        dlg.showModal();
      } else {
        dlg.setAttribute('open', '');
        dlg.classList.add('is-open-fallback');
        document.documentElement.style.overflow = 'hidden';
      }
    } catch {
      dlg.setAttribute('open', '');
      dlg.classList.add('is-open-fallback');
      document.documentElement.style.overflow = 'hidden';
    }
  }
  function closeDialog() {
    try { if (typeof dlg.close === 'function') dlg.close(); } finally {
      dlg.removeAttribute('open');
      dlg.classList.remove('is-open-fallback');
      document.documentElement.style.overflow = '';
    }
  }

  // —— 交互
  els.closeBtn?.addEventListener('click', (e) => {
    e.preventDefault();
    closeDialog();
  });
  dlg.addEventListener('close', () => {
    // 原生 close 触发也兜一层
    dlg.removeAttribute('open');
    dlg.classList.remove('is-open-fallback');
    document.documentElement.style.overflow = '';
  });
  // 退化模式：点击遮罩关闭
  dlg.addEventListener('click', (e) => {
    if (!dlg.classList.contains('is-open-fallback')) return;
    const r = els.card?.getBoundingClientRect();
    if (!r) return;
    const inside =
      e.clientX >= r.left && e.clientX <= r.right &&
      e.clientY >= r.top &&  e.clientY <= r.bottom;
    if (!inside) closeDialog();
  });

  // —— 对外：填充并打开
  function fmtDate(t){ return t ? new Date(t).toLocaleDateString() : 'Unknown'; }

  function open(m) {
    // 只在这里填充内容；字段缺失时给默认值
    els.lib.textContent = m._library || 'Unknown';
    if ('score' in m && m.score !== null && m.score !== undefined) {
      els.score.textContent = `Score: ${m.score}`;
      els.score.hidden = false;
    } else {
      els.score.hidden = true;
    }
    els.when.textContent = m.when_to_use || 'No specific guidance provided';
    els.content.textContent = m.content || 'No content available';
    els.author.textContent = m.author || 'Unknown';
    els.created.textContent = fmtDate(m.time_created);
    els.id.textContent = m.memory_id || 'N/A';
    els.ws.textContent = m.workspace_id || 'N/A';

    openDialog();
  }

  return { open, close: closeDialog };
}

  // —— Render — Libraries (stacked categories)
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
      const contributeChip = (cat === "Medical/Law/Education") ? `<span class="ml-chip contribute">Feel free to contribute</span>` : "";

      return `
      <section class="ml-section">
        <h3>${cat} ${betaChip} ${contributeChip}</h3>
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
    const libsShown = Object.values(CATEGORY_MAP)
  .reduce((acc, prefixes) => acc + prefixes.filter(p => availableLibs.includes(p)).length, 0);
    $("ml-count").textContent = libsShown;
    $("ml-total").textContent = libsShown;
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


    const modal = createMemoryModal();
    // modal binding
    [...elMemories.querySelectorAll(".ml-card-item")].forEach(card=>{
      card.addEventListener("click", ()=>{
        const absIdx = Number(card.getAttribute("data-idx"));
        const m = CURRENT_MEM_LIST[absIdx];
        modal.open(m);
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