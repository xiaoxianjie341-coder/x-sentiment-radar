# x-sentiment-radar

Sentiment-first X/Twitter topic radar for AI and Crypto operators.

This project is designed around one job:

`find rising topics -> inspect real replies -> summarize crowd emotion and disagreement -> surface borrowable viewpoints in Obsidian`

It is **not** an auto-posting tool.
It is **not** a final content judge.
It is a research assistant that helps the operator figure out:

- what is worth researching next
- what people are actually arguing about
- which replies are strong enough to borrow or cross-reference

## Main Command

```bash
python3 -m twitter_ops_agent.cli run-v2
```

If installed in editable mode:

```bash
twitter-ops-agent run-v2
```

## Obsidian Output

The product writes into:

- `00_今日雷达`
- `01_主题参考`
- `02_可借用观点`
- `03_处理记录`

Recommended operator flow:

1. Open `00_今日雷达`
2. Click one topic in `01_主题参考`
3. Open `02_可借用观点` if the topic is promising
4. Do your own deeper research before posting

## Minimum Setup

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

## Notes About AttentionVC

What this project uses well:

- `trending` for topic discovery
- `categories/insights` for category-level topic hints
- `articles` and optional `articles/rising` for article-side discovery
- `search` for normal tweets
- `tweet/replies` and `tweet/thread` for reply/context mining

Important limitation:

- article-side discovery is stronger than raw tweet-side discovery
- tweet-side “rising” still depends on our own ranking logic, not a first-class platform endpoint

## Current Maturity

Already working:

- topic-first radar flow
- reply fetching with pagination
- up to 100 reply samples per topic
- Obsidian radar/topic/viewpoint pages
- source links in radar

Still improving:

- tweet-side discovery quality
- high-quality reply reranking
- cleaner separation between weak-comment topics and strong-comment topics
