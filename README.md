# x-sentiment-radar

Sentiment-first X/Twitter topic radar for AI and Crypto operators.

这是一个面向 `AI / Crypto` 运营者的情绪优先研究助手。

它的核心任务不是自动发帖，而是：

`发现正在起势的主题 -> 抓原帖和真实回复 -> 提炼主情绪和主要分歧 -> 把可借用观点写进 Obsidian`

This project is **not**:

- an auto-posting tool
- a final content judge
- a full “one-click content machine”

This project **is**:

- a topic radar
- a reply / disagreement mining tool
- a research assistant for human operators

## Main Command / 主要命令

```bash
python3 -m twitter_ops_agent.cli run-v2
```

If installed in editable mode:

```bash
twitter-ops-agent run-v2
```

## Obsidian Output / Obsidian 输出结构

The product writes into:

- `00_今日雷达`
- `01_主题参考`
- `02_可借用观点`

系统会把结果写进：

- `00_今日雷达`
- `01_主题参考`
- `02_可借用观点`

Recommended operator flow / 推荐使用方式：

1. Open `00_今日雷达`
2. Click one topic in `01_主题参考`
3. Open `02_可借用观点` if the topic is promising
4. Do your own deeper research before posting

对应中文理解：

1. 先看 `今日雷达`
2. 再点进 `主题参考`
3. 如果这个主题值得继续挖，再看 `可借用观点`
4. 最后还是你自己继续研究，再决定发不发

## Minimum Setup / 最低配置

Copy the example config:

```bash
cp config/settings.example.toml config/settings.toml
```

Set at least:

```toml
obsidian_vault = "/absolute/path/to/Obsidian Vault"
obsidian_root = "/absolute/path/to/Obsidian Vault/推特运营Agent"

attentionvc_api_key = "avc_..."
attentionvc_base_url = "https://api.attentionvc.ai"

attentionvc_categories = ["ai", "crypto"]
attentionvc_source_mode = "mixed"
attentionvc_use_rising = false

attentionvc_search_queries = ["anthropic", "openai", "solana"]
attentionvc_search_limit_per_query = 3

attentionvc_article_min_views = 3000
attentionvc_article_min_likes = 30
attentionvc_article_min_replies = 10

attentionvc_tweet_min_views = 500
attentionvc_tweet_min_likes = 10
attentionvc_tweet_min_replies = 3

attentionvc_reply_sample_limit = 100
attentionvc_top_signal_count = 10

attentionvc_signal_min_views = 100
attentionvc_signal_min_likes = 2
attentionvc_signal_min_replies = 2
```

### What these settings mean / 这些配置是什么意思

- `attentionvc_source_mode`
  - `"mixed"`：同时参考主题文章和普通 tweet
  - `"tweets_only"`：只抓普通 tweet
  - `"articles_only"`：只抓文章

- `attentionvc_search_queries`
  - 你关心的基础主题词

- `attentionvc_article_min_*`
  - 文章类来源的最低门槛

- `attentionvc_tweet_min_*`
  - 普通 tweet 的最低门槛

- `attentionvc_reply_sample_limit = 100`
  - 每个主题最多抓 100 条回复样本

- `attentionvc_top_signal_count = 10`
  - 最后输出前 10 条高信号评论

## Notes About AttentionVC / 关于 AttentionVC

What this project uses well:

- `trending` for topic discovery
- `categories/insights` for category-level topic hints
- `articles` and optional `articles/rising` for article-side discovery
- `search` for normal tweets
- `tweet/replies` and `tweet/thread` for reply/context mining

这个项目目前主要用它来做：

- 热门主题发现
- 类别洞察
- 文章级别的起势发现
- 普通 tweet 搜索
- 回复抓取
- thread 上下文抓取

Important limitation / 重要限制：

- article-side discovery is stronger than raw tweet-side discovery
- tweet-side “rising” still depends on our own ranking logic

也就是说：

- 文章侧“起势”信号比 tweet 侧更强
- tweet 侧的“正在起势”目前还是我们自己算的，不是平台直接给的成品能力

## Current Maturity / 当前完成度

Already working / 已经完成的：

- topic-first radar flow
- reply fetching with pagination
- up to 100 reply samples per topic
- Obsidian radar/topic/viewpoint pages
- source links in radar

已经做到：

- 主题优先的发现流程
- 回复分页抓取
- 每个主题最多抓 100 条回复样本
- 写入 `雷达 / 主题参考 / 可借用观点`
- 雷达页里可直接点原推文

Still improving / 还在继续优化的：

- tweet-side discovery quality
- high-quality reply reranking
- cleaner separation between weak-comment topics and strong-comment topics

还差的主要是：

- tweet 侧发现质量还不够强
- 高质量评论排序还不够聪明
- 还需要更好地区分“评论区很弱”和“评论区真有料”的主题
