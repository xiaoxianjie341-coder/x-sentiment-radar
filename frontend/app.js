const dataPath = "../data/cross-signal/latest.json";

const candidateCountEl = document.querySelector("#candidate-count");
const newCandidateCountEl = document.querySelector("#new-candidate-count");
const passedCountEl = document.querySelector("#passed-count");
const breakingFeedEl = document.querySelector("#breaking-feed");
const newCandidatesEl = document.querySelector("#new-candidates");
const reviewedCandidatesEl = document.querySelector("#reviewed-candidates");
const passedTopicsEl = document.querySelector("#passed-topics");
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
  renderBreakingFeed(data);
  renderNewCandidates(data);
  renderReviewedCandidates(data);
  renderPassedTopics(data);
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

  if (!candidates.length) {
    breakingFeedEl.innerHTML = emptyState("当前没有抓到 Breaking 事件。");
    return;
  }

  breakingFeedEl.innerHTML = candidates
    .map((item, index) => {
      const isNew = newCandidateSet.has(item.slug);
      return `
        <article class="feed-item">
          <div class="feed-topline">
            <span class="rank-chip">#${index + 1}</span>
            <span class="state-chip ${isNew ? "" : "is-seen"}">${isNew ? "NEW" : "SEEN"}</span>
          </div>
          <h3><a href="${escapeHtml(item.market_url)}" target="_blank" rel="noreferrer">${escapeHtml(item.title)}</a></h3>
          <div class="feed-meta">
            ${tagChip(item.category_slug || "uncategorized")}
            ${item.secondary_category_slug ? tagChip(item.secondary_category_slug) : ""}
            ${tagChip(item.source_label || "breaking")}
          </div>
          <div class="feed-numbers">
            ${statBox("24h Volume", formatCompact(item.volume_24h))}
            ${statBox("Liquidity", formatCompact(item.liquidity))}
          </div>
        </article>
      `;
    })
    .join("");
}

function renderNewCandidates(data) {
  const items = Array.isArray(data.new_candidates) ? data.new_candidates : [];

  if (!items.length) {
    newCandidatesEl.innerHTML = emptyState("这一轮没有新进入 Breaking 的事件。");
    return;
  }

  newCandidatesEl.innerHTML = items
    .map(
      (item) => `
        <article class="compact-item">
          <strong>${escapeHtml(item.title)}</strong>
          <div class="compact-meta">
            ${tagChip(item.category_slug || "uncategorized")}
            ${item.secondary_category_slug ? tagChip(item.secondary_category_slug) : ""}
          </div>
        </article>
      `
    )
    .join("");
}

function renderPassedTopics(data) {
  const topics = Array.isArray(data.topics) ? data.topics : [];

  if (!topics.length) {
    passedTopicsEl.innerHTML = emptyState("这一轮 Grok 没有放行任何 topic。");
    return;
  }

  passedTopicsEl.innerHTML = topics
    .map((topic) => {
      const posts = Array.isArray(topic.top_posts) ? topic.top_posts : [];
      return `
        <article class="topic-card">
          <h3>${escapeHtml(topic.market_title)}</h3>
          <p>${escapeHtml(topic.angle_summary || "Grok 认为这个事件已经形成了可跟进的讨论。")}</p>
          <div class="topic-stats">
            ${statBox("Distinct Posts", topic.distinct_post_count ?? 0)}
            ${statBox("Distinct Accounts", topic.distinct_account_count ?? 0)}
          </div>
          <div class="topic-meta">
            ${tagChip(topic.source_label || "breaking")}
            ${(topic.queries || []).map((query) => tagChip(query)).join("")}
          </div>
          <div class="topic-posts">
            ${posts
              .map(
                (post) => `
                  <article class="topic-post">
                    <a href="${escapeHtml(post.url)}" target="_blank" rel="noreferrer">${escapeHtml(post.author_handle || post.url)}</a>
                    <p>${escapeHtml(post.text || "")}</p>
                  </article>
                `
              )
              .join("")}
          </div>
        </article>
      `;
    })
    .join("");
}

function renderReviewedCandidates(data) {
  const reviews = Array.isArray(data.reviewed_candidates) ? data.reviewed_candidates : [];

  if (!reviews.length) {
    reviewedCandidatesEl.innerHTML = emptyState("这一轮还没有完成任何 Grok review。");
    return;
  }

  reviewedCandidatesEl.innerHTML = reviews
    .map((review) => {
      const posts = Array.isArray(review.top_posts) ? review.top_posts : [];
      const cardClass = review.is_viral ? "topic-card is-passed" : "topic-card is-rejected";
      return `
        <article class="${cardClass}">
          <h3>${escapeHtml(review.market_title)}</h3>
          <p>${escapeHtml(review.angle_summary || review.reason_if_not_viral || "Grok 没有给出稳定角度。")}</p>
          <div class="topic-stats">
            ${statBox("Confidence", review.confidence ?? 0)}
            ${statBox("Posts Seen", review.distinct_post_count ?? 0)}
          </div>
          <div class="topic-meta">
            ${tagChip(review.is_viral ? "passed" : "rejected")}
            ${(review.queries || []).map((query) => tagChip(query)).join("")}
          </div>
          ${
            review.reason_if_not_viral
              ? `<p>${escapeHtml(`未通过原因：${review.reason_if_not_viral}`)}</p>`
              : ""
          }
          <div class="topic-posts">
            ${
              posts.length
                ? posts
                    .map(
                      (post) => `
                        <article class="topic-post">
                          <a href="${escapeHtml(post.url)}" target="_blank" rel="noreferrer">${escapeHtml(post.author_handle || post.url)}</a>
                          <p>${escapeHtml(post.text || "")}</p>
                        </article>
                      `
                    )
                    .join("")
                : `<div class="empty-state">这条 review 没带可展示帖子。</div>`
            }
          </div>
        </article>
      `;
    })
    .join("");
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
