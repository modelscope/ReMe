# Ready-to-Use Memories

<div id="memory-lib-root" class="ml-prose-container">
  <!-- 工具条 -->
  <div class="ml-card">
    <div class="ml-toolbar">
      <div class="ml-input-wrap">
        <svg class="ml-icon" viewBox="0 0 24 24" aria-hidden="true">
          <path d="M15.5 14h-.79l-.28-.27A6.471 6.471 0 0 0 16 9.5 6.5 6.5 0 1 0 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"/>
        </svg>
        <input id="ml-search" placeholder="Search memories..." />
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
    <div class="ml-muted">Loading memories…</div>
  </div>
  <div id="ml-error" class="ml-error" hidden>
    <div class="ml-error-icon">⚠️</div>
    <div class="ml-muted">Failed to load memories.</div>
    <button id="ml-retry" class="ml-btn">Try again</button>
  </div>

  <!-- 面包屑 -->
  <div id="ml-crumb" class="ml-crumb" hidden>
    <button id="ml-back" class="ml-link">← Back to memory home</button>
    <div class="ml-crumb-title" id="ml-crumb-title">memories</div>
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
<div id="ml-modal" class="ml-modal" hidden aria-hidden="true">
  <div class="ml-modal-backdrop" data-ml-close></div>
  <div class="ml-modal-card" role="dialog" aria-modal="true" aria-labelledby="ml-modal-title">
    <div class="ml-modal-header">
      <div>
        <div class="ml-chip" id="ml-modal-lib"></div>
        <div class="ml-chip success" id="ml-modal-score" hidden></div>
      </div>
      <button class="ml-close" type="button" aria-label="Close" data-ml-close>✕</button>
    </div>

    <h2 id="ml-modal-title" class="sr-only">Memory details</h2>

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
      <button class="ml-btn secondary" type="button" data-ml-close>Close</button>
    </div>
  </div>
</div>