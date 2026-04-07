const dataPath = "../data/cross-signal/latest.json";

const candidateCountEl = document.querySelector("#candidate-count");
const newCandidateCountEl = document.querySelector("#new-candidate-count");
const passedCountEl = document.querySelector("#passed-count");
const breakingFeedEl = document.querySelector("#breaking-feed");
const sweepSummaryEl = document.querySelector("#sweep-summary");
const statusLegendEl = document.querySelector("#status-legend");
const quickActionsEl = document.querySelector("#quick-actions");
const rawPreviewEl = document.querySelector("#raw-preview");

init().catch((error) => {
  rawPreviewEl.textContent = String(error?.stack || error);
});

async function init() {
  const response = await fetch(dataPath, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`Failed to load ${dataPath}: HTTP ${response.status}`);
  }
  const data = await response.json();
  renderMetrics(data);
  renderSidePanel(data);
  renderBreakingFeed(data);
  rawPreviewEl.textContent = JSON.stringify(data, null, 2);
}

function renderMetrics(data) {
  candidateCountEl.textContent = data.candidate_count ?? 0;
  newCandidateCountEl.textContent = data.new_candidate_count ?? 0;
  passedCountEl.textContent = data.passed_count ?? 0;
}

function renderBreakingFeed(data) {
  const candidates = Array.isArray(data.candidates) ? data.candidates : [];
  const newCandidateSet = new Set((data.new_candidates || []).map((item) => item.slug));
  const reviewMap = new Map((data.reviewed_candidates || []).map((item) => [item.slug, item]));

  if (!candidates.length) {
    breakingFeedEl.innerHTML = emptyState("当前没有抓到 Breaking 事件。");
    return;
  }

  breakingFeedEl.innerHTML = candidates
    .map((item, index) => {
      const isNew = newCandidateSet.has(item.slug);
      const review = reviewMap.get(item.slug);
      const status = review ? (review.is_viral ? "passed" : "rejected") : "pending";
      return `
        <details class="feed-item feed-item--${status}" ${index < 2 ? "open" : ""}>
          <summary class="feed-summary">
            <div class="feed-topline">
              <span class="rank-chip">#${index + 1}</span>
              <div class="feed-status-group">
                <span class="state-chip ${isNew ? "" : "is-seen"}">${isNew ? "NEW" : "SEEN"}</span>
                <span class="state-chip state-chip--${status}">${status.toUpperCase()}</span>
              </div>
            </div>
            <h3>${escapeHtml(item.title)}</h3>
            <div class="feed-meta">
              ${tagChip(item.category_slug || "uncategorized")}
              ${item.secondary_category_slug ? tagChip(item.secondary_category_slug) : ""}
              ${tagChip(item.source_label || "breaking")}
            </div>
            <div class="feed-numbers">
              ${statBox("24h Volume", formatCompact(item.volume_24h))}
              ${statBox("Liquidity", formatCompact(item.liquidity))}
            </div>
          </summary>
          <div class="feed-drawer">
            <div class="drawer-grid">
              <div class="drawer-card">
                <p class="console-label">Market</p>
                <a href="${escapeHtml(item.market_url)}" target="_blank" rel="noreferrer">${escapeHtml(item.market_url)}</a>
              </div>
              <div class="drawer-card">
                <p class="console-label">Grok Verdict</p>
                <strong>${review ? escapeHtml(review.is_viral ? "Passed" : "Rejected") : "Pending"}</strong>
              </div>
              <div class="drawer-card">
                <p class="console-label">Confidence</p>
                <strong>${review ? escapeHtml(String(review.confidence ?? 0)) : "--"}</strong>
              </div>
              <div class="drawer-card">
                <p class="console-label">Distinct Accounts</p>
                <strong>${review ? escapeHtml(String(review.distinct_account_count ?? 0)) : "--"}</strong>
              </div>
            </div>
            <div class="drawer-copy">
              <h4>Angle Summary</h4>
              <p>${escapeHtml(review?.angle_summary || "这条事件还没完成 Grok review。")}</p>
            </div>
            ${
              review?.reason_if_not_viral
                ? `<div class="drawer-copy"><h4>Why Not Passed</h4><p>${escapeHtml(review.reason_if_not_viral)}</p></div>`
                : ""
            }
            <div class="drawer-copy">
              <h4>Top X Posts</h4>
              <div class="topic-posts">
                ${
                  review?.top_posts?.length
                    ? review.top_posts
                        .map(
                          (post) => `
                            <article class="topic-post">
                              <a href="${escapeHtml(post.url)}" target="_blank" rel="noreferrer">${escapeHtml(post.author_handle || post.url)}</a>
                              <p>${escapeHtml(post.text || "")}</p>
                            </article>
                          `
                        )
                        .join("")
                    : `<div class="empty-state">这条卡片目前还没有可展示的 X 帖子。</div>`
                }
              </div>
            </div>
          </div>
        </details>
      `;
    })
    .join("");
}

function renderSidePanel(data) {
  const reviews = Array.isArray(data.reviewed_candidates) ? data.reviewed_candidates : [];
  const passed = reviews.filter((item) => item.is_viral).length;
  const rejected = reviews.filter((item) => !item.is_viral).length;
  const pending = Math.max((data.candidate_count ?? 0) - reviews.length, 0);

  sweepSummaryEl.innerHTML = [
    compactLine("Breaking scanned", data.candidate_count ?? 0),
    compactLine("Reviewed this run", reviews.length),
    compactLine("Passed", passed),
    compactLine("Rejected", rejected),
    compactLine("Pending", pending),
  ].join("");

  statusLegendEl.innerHTML = [
    legendCard("NEW", "刚进入这轮关注范围的 Breaking 事件。"),
    legendCard("PASSED", "Grok 认为它已经在 X 上形成值得跟进的传播。"),
    legendCard("REJECTED", "Grok 已经看过，但觉得还没有形成你要的传播级别。"),
    legendCard("PENDING", "这轮还没完成 review，或者还没开始跑。"),
  ].join("");

  quickActionsEl.innerHTML = [
    actionCard("手动看当前轮", "./scripts/run-cross-signal-grok.sh"),
    actionCard("强制整页重跑", "./scripts/review-all-breaking-now.sh"),
    actionCard("初始化 seen state", "./scripts/prime-cross-signal-state.sh"),
    actionCard("安装半小时巡检", "./scripts/install-cross-signal-cron.sh"),
  ].join("");
}

function statBox(label, value) {
  return `
    <div class="stat-box">
      <span>${escapeHtml(String(label))}</span>
      <strong>${escapeHtml(String(value))}</strong>
    </div>
  `;
}

function tagChip(value) {
  return `<span class="tag-chip">${escapeHtml(String(value))}</span>`;
}

function compactLine(label, value) {
  return `
    <article class="compact-item">
      <span class="console-label">${escapeHtml(String(label))}</span>
      <strong>${escapeHtml(String(value))}</strong>
    </article>
  `;
}

function legendCard(title, desc) {
  return `
    <article class="compact-item">
      <strong>${escapeHtml(title)}</strong>
      <p>${escapeHtml(desc)}</p>
    </article>
  `;
}

function actionCard(title, command) {
  return `
    <article class="compact-item">
      <strong>${escapeHtml(title)}</strong>
      <p><code>${escapeHtml(command)}</code></p>
    </article>
  `;
}

function emptyState(text) {
  return `<div class="empty-state">${escapeHtml(text)}</div>`;
}

function formatCompact(value) {
  const number = Number(value || 0);
  if (number >= 1_000_000) return `${(number / 1_000_000).toFixed(1)}M`;
  if (number >= 1_000) return `${(number / 1_000).toFixed(1)}K`;
  return String(Math.round(number));
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}
