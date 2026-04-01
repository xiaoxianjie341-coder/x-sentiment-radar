# x-sentiment-radar

## 中文版

`x-sentiment-radar` 是一个面向 `AI / Crypto` 运营者的情绪优先研究助手。

它的核心任务不是自动发帖，而是：

`发现正在起势的主题 -> 抓原帖和真实回复 -> 提炼主情绪和主要分歧 -> 把可借用观点写进 Obsidian`

它不是：

- 自动发帖工具
- 最终内容裁决器
- 一键生成爆款内容的机器

它是：

- 一个主题雷达
- 一个评论区/分歧挖掘工具
- 一个帮助你继续人工研究的助手

### 主要命令

```bash
python3 -m twitter_ops_agent.cli run-v2
```

如果你本地已经 `pip install -e .`：

```bash
twitter-ops-agent run-v2
```

### Obsidian 输出

系统会把结果写进：

- `00_今日雷达`
- `01_主题参考`
- `02_可借用观点`

推荐使用顺序：

1. 先看 `00_今日雷达`
2. 再点进 `01_主题参考`
3. 如果这个主题值得继续挖，再看 `02_可借用观点`
4. 最后还是你自己继续研究，再决定发不发

### 最低配置

先复制配置文件：

```bash
cp config/settings.example.toml config/settings.toml
```

至少要配置这些：

```toml
obsidian_vault = "/absolute/path/to/Obsidian Vault"
obsidian_root = "/absolute/path/to/Obsidian Vault/推特运营Agent"

attentionvc_api_key = "avc_..."
attentionvc_base_url = "https://api.attentionvc.ai"

attentionvc_categories = ["ai", "crypto"]
attentionvc_source_mode = "articles_only"
attentionvc_use_rising = true

attentionvc_search_queries = ["anthropic", "openai", "solana"]
attentionvc_search_limit_per_query = 3

attentionvc_article_min_views = 2000
attentionvc_article_min_likes = 20
attentionvc_article_min_replies = 5

attentionvc_tweet_min_views = 500
attentionvc_tweet_min_likes = 10
attentionvc_tweet_min_replies = 3

attentionvc_reply_sample_limit = 100
attentionvc_top_signal_count = 10

attentionvc_signal_min_views = 0
attentionvc_signal_min_likes = 0
attentionvc_signal_min_replies = 0
```

### 配置含义

- `attentionvc_source_mode`
  - `"mixed"`：同时参考主题文章和普通 tweet
  - `"tweets_only"`：只抓普通 tweet
  - `"articles_only"`：只抓文章。对新用户最稳，推荐默认使用这个。

- `attentionvc_search_queries`
  - 你想重点盯的基础主题词

- `attentionvc_article_min_*`
  - 文章类来源的最低门槛

- `attentionvc_tweet_min_*`
  - 普通 tweet 的最低门槛

- `attentionvc_reply_sample_limit = 100`
  - 每个主题最多抓 100 条回复样本

- `attentionvc_top_signal_count = 10`
  - 默认输出前 10 条评论，并在笔记里按情绪分组展示

- `attentionvc_signal_min_* = 0`
  - 默认不按最低浏览 / 最低点赞硬过滤评论，避免把低互动但有价值的回复提前筛掉

### 关于 AttentionVC

这个项目目前主要用它来做：

- 热门主题发现
- 类别洞察
- 文章级别的起势发现
- 普通 tweet 搜索
- 回复抓取
- thread 上下文抓取

当前限制：

- 文章侧“起势”信号比 tweet 侧更强
- tweet 侧“正在起势”目前还是我们自己算的，不是平台直接给的成品能力

### 当前完成度

已经做到：

- 主题优先的发现流程
- 回复分页抓取
- 每个主题最多抓 100 条回复样本
- 写入 `雷达 / 主题参考 / 可借用观点`
- 主题参考页里默认展示 10 条评论，并按情绪分组
- 雷达页里可直接点原推文

还在继续优化：

- tweet 侧发现质量还不够强
- 高质量评论排序还不够聪明
- 还需要更好地区分“评论区很弱”和“评论区真有料”的主题

---

## English

`x-sentiment-radar` is a sentiment-first X/Twitter research assistant for `AI / Crypto` operators.

Its core job is:

`find rising topics -> inspect real replies -> summarize crowd emotion and disagreement -> surface borrowable viewpoints in Obsidian`

It is **not**:

- an auto-posting tool
- a final content judge
- a one-click content machine

It **is**:

- a topic radar
- a reply / disagreement mining tool
- a research assistant for human operators

### Main Command

```bash
python3 -m twitter_ops_agent.cli run-v2
```

If installed in editable mode:

```bash
twitter-ops-agent run-v2
```

### Obsidian Output

The project writes into:

- `00_今日雷达`
- `01_主题参考`
- `02_可借用观点`

Recommended operator flow:

1. Open `00_今日雷达`
2. Click one topic in `01_主题参考`
3. Open `02_可借用观点` if the topic looks promising
4. Continue manual research before posting

### Minimum Setup

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

attentionvc_signal_min_views = 0
attentionvc_signal_min_likes = 0
attentionvc_signal_min_replies = 0
```

### What These Settings Mean

- `attentionvc_source_mode`
  - `"mixed"`: use both article-side topic signals and normal tweets
  - `"tweets_only"`: normal tweet discovery only
  - `"articles_only"`: article discovery only

- `attentionvc_search_queries`
  - base topic keywords you care about

- `attentionvc_article_min_*`
  - minimum thresholds for article-side inputs

- `attentionvc_tweet_min_*`
  - minimum thresholds for normal tweet-side inputs

- `attentionvc_reply_sample_limit = 100`
  - fetch up to 100 reply samples per topic

- `attentionvc_top_signal_count = 10`
  - keep 10 comments by default and show them grouped by audience emotion in the note

- `attentionvc_signal_min_* = 0`
  - do not hard-filter low-engagement replies by default, so sparse but useful comments still survive

### AttentionVC Reality

This project currently uses AttentionVC for:

- trending topic discovery
- category insights
- article-side rising detection
- normal tweet search
- reply fetching
- thread context fetching

Current limitation:

- article-side discovery is stronger than raw tweet-side discovery
- tweet-side “rising” still depends on our own ranking logic

### Current Maturity

Already working:

- topic-first radar flow
- reply pagination
- up to 100 reply samples per topic
- radar / topic / viewpoint pages in Obsidian
- top 10 comments grouped by emotion inside topic notes
- source links in radar

Still improving:

- tweet-side discovery quality
- high-quality reply reranking
- better separation between weak-comment topics and strong-comment topics

### Recommended default for first-time users / 推荐默认方式

For the first run, the most stable setup is:

- `attentionvc_source_mode = "articles_only"`
- `attentionvc_use_rising = true`
- `attentionvc_categories = ["ai", "crypto"]`
- `attentionvc_reply_sample_limit = 100`

第一次使用时，最推荐的默认方式是：

- 先用 `articles_only`
- 打开 `use_rising`
- 先只看 `AI / Crypto`
- 每个主题抓 `100` 条回复样本

这样安装后更容易直接跑通，也更接近“傻瓜式上手”。
