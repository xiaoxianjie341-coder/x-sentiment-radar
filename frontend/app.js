const dataPath = "../data/cross-signal/latest.json";

const candidateCountEl = document.querySelector("#candidate-count");
const newCandidateCountEl = document.querySelector("#new-candidate-count");
const passedCountEl = document.querySelector("#passed-count");
const breakingFeedEl = document.querySelector("#breaking-feed");
const sweepSummaryEl = document.querySelector("#sweep-summary");
const statusLegendEl = document.querySelector("#status-legend");
const quickActionsEl = document.querySelector("#quick-actions");
const runCheckBtn = document.querySelector("#run-check-btn");
const reviewAllBtn = document.querySelector("#review-all-btn");
const scheduleBtn = document.querySelector("#schedule-btn");
const actionStatusEl = document.querySelector("#action-status");

let latestData = null;
let scheduleEnabled = false;
let reviewAllRunning = false;
let reviewAllPoller = null;

init().catch((error) => {
  actionStatusEl.textContent = `页面加载失败：${String(error?.message || error)}`;
});

async function init() {
  const [data, meta] = await Promise.all([loadData(), loadMeta()]);
  latestData = data;
  scheduleEnabled = Boolean(meta.schedule_enabled);
  reviewAllRunning = Boolean(meta.review_all_running);
  bindActions();
  render(data);
}

async function loadData() {
  const response = await fetch(dataPath, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`Failed to load ${dataPath}: HTTP ${response.status}`);
  }
  return response.json();
}

async function loadMeta() {
  const response = await fetch("/api/meta", { cache: "no-store" });
  if (!response.ok) {
    return { schedule_enabled: false };
  }
  return response.json();
}

function render(data) {
  renderMetrics(data);
  renderSidePanel(data);
  renderBreakingFeed(data);
  updateScheduleButton();
}

function bindActions() {
  runCheckBtn.addEventListener("click", () => triggerRun("incremental"));
  reviewAllBtn.addEventListener("click", () => triggerRun("review_all"));
  scheduleBtn.addEventListener("click", toggleSchedule);
  updateScheduleButton();
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
  const orderedCandidates = [...candidates].sort((left, right) => {
    const leftReview = reviewMap.get(left.slug);
    const rightReview = reviewMap.get(right.slug);
    const leftRank = leftReview ? (leftReview.is_viral ? 0 : 1) : 2;
    const rightRank = rightReview ? (rightReview.is_viral ? 0 : 1) : 2;
    if (leftRank !== rightRank) return leftRank - rightRank;
    return 0;
  });

  if (!orderedCandidates.length) {
    breakingFeedEl.innerHTML = emptyState("当前没有抓到 Breaking 事件。");
    return;
  }

  breakingFeedEl.innerHTML = orderedCandidates
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
              ${statBox("Current", formatPercent(item.current_probability))}
              ${statBox("24h Change", formatChange(item.probability_change_24h, item.change_direction))}
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
    actionCard("立即检查新事件", "按钮会运行增量检查"),
    actionCard("重审当前整页", "按钮会让当前全部 Breaking 事件都过一遍 Grok"),
    actionCard("30 分钟自动检查", scheduleEnabled ? "已开启，可点击按钮关闭" : "当前关闭，可点击按钮开启"),
    actionCard("已通过热点", `${data.passed_count ?? 0} 条，现在会在左侧自动置顶`),
  ].join("");
}

async function triggerRun(mode) {
  setBusy(true, mode === "incremental" ? "正在检查有没有新事件..." : "正在重审当前整页，请稍等...");
  try {
    const response = await fetch("/api/run-check", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mode }),
    });
    const payload = await response.json();
    if (!response.ok || !payload.ok) {
      throw new Error(payload.stderr || payload.stdout || "检查失败");
    }
    if (mode === "review_all" && payload.running) {
      reviewAllRunning = true;
      latestData = payload.latest || latestData;
      if (latestData) render(latestData);
      actionStatusEl.textContent = payload.started ? "整页重审已经在后台开始运行，你可以直接刷新观察结果。" : "整页重审已在后台运行中。";
      startReviewPolling();
      return;
    }
    latestData = payload.latest;
    render(latestData);
    actionStatusEl.textContent = mode === "incremental" ? "已完成新事件检查。" : "已完成整页重审。";
  } catch (error) {
    actionStatusEl.textContent = `执行失败：${String(error.message || error)}`;
  } finally {
    setBusy(false);
  }
}

async function toggleSchedule() {
  setBusy(true, scheduleEnabled ? "正在关闭自动检查..." : "正在开启每30分钟自动检查...");
  try {
    const response = await fetch("/api/toggle-schedule", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ enabled: !scheduleEnabled }),
    });
    const payload = await response.json();
    if (!response.ok || !payload.ok) {
      throw new Error(payload.stderr || payload.stdout || "定时设置失败");
    }
    scheduleEnabled = Boolean(payload.schedule_enabled);
    updateScheduleButton();
    actionStatusEl.textContent = scheduleEnabled ? "已开启每30分钟自动检查。" : "已关闭自动检查。";
    if (latestData) {
      renderSidePanel(latestData);
    }
  } catch (error) {
    actionStatusEl.textContent = `定时设置失败：${String(error.message || error)}`;
  } finally {
    setBusy(false);
  }
}

function setBusy(busy, text = "") {
  runCheckBtn.disabled = busy;
  reviewAllBtn.disabled = busy && !reviewAllRunning;
  scheduleBtn.disabled = busy;
  if (text) actionStatusEl.textContent = text;
}

function updateScheduleButton() {
  scheduleBtn.textContent = scheduleEnabled ? "关闭每30分钟自动检查" : "开启每30分钟自动检查";
  reviewAllBtn.textContent = reviewAllRunning ? "整页重审进行中..." : "重审当前整页";
}

function startReviewPolling() {
  if (reviewAllPoller) return;
  reviewAllPoller = window.setInterval(async () => {
    try {
      const response = await fetch("/api/job-status", { cache: "no-store" });
      if (!response.ok) return;
      const payload = await response.json();
      reviewAllRunning = Boolean(payload.review_all_running);
      if (payload.latest) {
        latestData = payload.latest;
        render(latestData);
      }
      if (!reviewAllRunning) {
        actionStatusEl.textContent = "整页重审已完成。";
        stopReviewPolling();
      } else {
        actionStatusEl.textContent = "整页重审进行中，结果会逐步写入卡片。";
        updateScheduleButton();
      }
    } catch {
      // Keep polling quiet on transient failures.
    }
  }, 2500);
}

function stopReviewPolling() {
  if (reviewAllPoller) {
    window.clearInterval(reviewAllPoller);
    reviewAllPoller = null;
  }
  reviewAllRunning = false;
  runCheckBtn.disabled = false;
  reviewAllBtn.disabled = false;
  scheduleBtn.disabled = false;
  updateScheduleButton();
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

function formatPercent(value) {
  const number = Number(value || 0);
  return `${number.toFixed(number >= 10 ? 1 : 2).replace(/\.0$/, "")}%`;
}

function formatChange(value, direction) {
  const number = Number(value || 0);
  const prefix = direction === "down" ? "-" : "+";
  return `${prefix}${number.toFixed(number >= 10 ? 1 : 2).replace(/\.0$/, "")}%`;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}
