# x-sentiment-radar

## 中文版

`x-sentiment-radar` 是一个面向 `AI / Crypto` 运营者的情绪优先研究助手。

它当前做的是：

`发现起势主题 -> 抓原帖 / 回复 / thread / 相关讨论 -> 提炼主情绪和主要分歧 -> 把可借用观点写进 Obsidian`

它不是：

- 自动发帖工具
- 最终内容裁决器
- 一键生成爆款内容的机器

它是：

- 一个主题雷达
- 一个评论区 / 分歧挖掘工具
- 一个帮助你继续人工研究的助手

### 当前已经实现的能力

- `doctor`：检查当前解析到的 `obsidian_root` 和 `sqlite_db`
- `run-v2`：执行完整的主题发现和写入流程
- 支持 `AttentionVC` 或 `XHunt + twscrape` 做主题发现和原帖补全
- 支持 `article / tweet / related discussion` 多来源补充
- 每个主题最多抓 `100` 条回复样本
- 默认尽量保留 `10` 条评论用于输出
- 默认不按最低浏览 / 最低点赞硬砍评论
- 主题页里输出：
  - 当前主情绪
  - 情绪分布
  - 主要分歧点
  - 高质量评论
  - 按情绪分类看评论
- 写入 `00_今日雷达 / 01_主题参考 / 02_可借用观点`
- 用本地 SQLite 记录 `last_seen_attention_v2_ids`，避免重复处理同一批主题
- 可选接入 `OpenAI-compatible` 的 writer，用模型替代内置启发式总结

### 安装

要求：

- `Python >= 3.14`
- 二选一：
  - 一个可用的 `AttentionVC API key`
  - 或一个可用的 `twscrape` 账号池 / cookies
- 一个你想写入的 `Obsidian` 路径

推荐安装方式：

```bash
git clone https://github.com/xiaoxianjie341-coder/x-sentiment-radar.git
cd x-sentiment-radar
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

安装完成后，推荐用这个命令，不要直接依赖未安装状态下的 `python -m ...`：

```bash
twitter-ops-agent doctor
twitter-ops-agent run-v2
```

如果你已经配好了本地浏览器会话，想直接跑免费的 `XHunt + browser-session` 链路，也可以直接用：

```bash
./scripts/run-xhunt-free.sh
```

### 第一次配置

先复制配置文件：

```bash
cp config/settings.example.toml config/settings.toml
```

新用户至少要改这几个：

```toml
obsidian_vault = "/absolute/path/to/Obsidian Vault"
obsidian_root = "/absolute/path/to/Obsidian Vault/推特运营Agent"

sqlite_db = "/absolute/path/to/your/sqlite.sqlite3"
```

免费低风控模式推荐这样配：

```toml
twscrape_db = "data/twscrape/accounts.db"
twscrape_search_enabled = false

xhunt_groups = ["cn", "global"]
xhunt_hours = 24
xhunt_limit = 15
xhunt_min_views = 1000
xhunt_min_likes = 10

attentionvc_tweet_min_views = 500
attentionvc_tweet_min_likes = 10
attentionvc_reply_sample_limit = 100
attentionvc_top_signal_count = 10
```

如果你想继续用付费模式，再补：

```toml
attentionvc_api_key = "avc_..."
attentionvc_base_url = "https://api.attentionvc.ai"
```

### 最重要的配置项说明

- `obsidian_vault`
  - 你的 Obsidian Vault 根目录

- `obsidian_root`
  - 这个项目真正写文件的目录
  - 项目会自动创建这 3 个子目录：
    - `00_今日雷达`
    - `01_主题参考`
    - `02_可借用观点`

- `sqlite_db`
  - 本地状态数据库
  - 这里会保存 `last_seen_attention_v2_ids` 或 `last_seen_xhunt_v2_ids`
  - 如果你想重新模拟“第一次运行”，请换一个新的 `sqlite_db` 路径

- `twscrape_db`
  - `twscrape` 的账号池数据库
  - 免费模式下 `run-v2` 会从这里读取账号 / cookies

- `twscrape_search_enabled = false`
  - 默认关闭关键词搜索 fallback
  - 这样更低风控，只做“原帖详情 + 顶层回复”抓取

- `xhunt_*`
  - 免费模式的发现入口
  - 默认会同时抓 `cn + global` 两个榜单
  - 每个榜单都会取过去 `24h` 的前 `15` 条，再用 `twscrape` 补原帖全文和回复

- `attentionvc_source_mode`
  - `"articles_only"`：只抓文章型主题。第一次使用最稳
  - `"tweets_only"`：只抓普通 tweet
  - `"mixed"`：两边都抓

- `attentionvc_use_rising`
  - 是否使用 rising 文章入口
  - 当前默认推荐打开

- `attentionvc_reply_sample_limit = 100`
  - 每个主题最多抓 `100` 条回复样本
  - 对 `twscrape` 低风控模式，推荐先降到 `20-30`

- `attentionvc_top_signal_count = 10`
  - 最终尽量保留 `10` 条评论用于输出

- `attentionvc_signal_min_* = 0`
  - 默认不按浏览 / 点赞 / 回复做硬门槛过滤
  - 这样低互动但有价值的评论也能保留下来

- `writer_*`
  - 可选
  - 如果你接了一个兼容 OpenAI API 的模型服务，评论总结会优先走 LLM
  - 不填则走内置启发式总结

### 第一次运行

先检查当前实际会写到哪里：

```bash
twitter-ops-agent doctor --json
```

如果输出里的 `obsidian_root` 和 `sqlite_db` 是你预期的，再执行：

```bash
twitter-ops-agent run-v2
```

成功时会返回类似：

```json
{
  "discovered_count": 12,
  "selected_count": 12,
  "radar_written": 1,
  "topic_notes_written": 12,
  "viewpoint_notes_written": 12
}
```

### Obsidian 里会看到什么

`00_今日雷达`

- 每天一张雷达页
- 每个主题会显示：
  - 赛道
  - 原推文链接
  - 当前主情绪
  - 主要分歧
  - 跳转到主题参考和可借用观点

`01_主题参考`

- 这个主题是什么
- 原始内容
- 现在大家在聊什么
- 当前主情绪
- 情绪分布
- 主要分歧点
- 高质量评论
- 按情绪分类看评论
- 可继续研究的方向

`02_可借用观点`

- 最值得借的观点
- 可交叉引用评论
- 可以继续展开的方向

推荐使用顺序：

1. 先看 `00_今日雷达`
2. 再点进 `01_主题参考`
3. 如果这个主题值得继续挖，再看 `02_可借用观点`
4. 最后还是你自己继续研究，再决定发不发

### 新用户最容易卡住的地方

- 没有先 `pip install -e .`
  - 推荐直接使用 `twitter-ops-agent ...`

- `attentionvc_api_key` 不可用
  - 现在不是必填
  - 如果配置了空 key，不会报错，但会回退到 `XHunt + twscrape`
  - 没 credits 会返回 `402`
  - 请求太密会返回 `429`

- `twscrape` 账号池没有准备好
  - 免费模式下会直接报错
  - 推荐先确认 `accounts.db` 里有可用 cookies

- `obsidian_root` 配到了一个你当前 Obsidian 没打开的目录
  - 文件其实已经写到磁盘上了
  - 但如果那个目录不是你当前打开的 vault，你不会在 Obsidian 侧边栏里直接看到

- 复跑时没换 `sqlite_db`
  - 由于 `last_seen_attention_v2_ids` 已经存在，第二次不一定会再出同样主题

### 当前限制

- `XHunt` 目前走的是公共页面解析，不是官方 API
- 免费模式下 `twscrape` 默认只抓原帖详情和顶层回复，不主动放大搜索面
- tweet 侧“正在起势”不是平台现成信号，而是本地排序近似
- `doctor` 目前主要检查路径，不会提前帮你验证 `AttentionVC` credits 或 `twscrape` 账号健康
- 大批量跑时可能会撞到 `AttentionVC` 或 `twscrape` 的各自限制

---

## English

`x-sentiment-radar` is a sentiment-first X/Twitter research assistant for `AI / Crypto` operators.

Current pipeline:

`discover rising topics -> fetch source tweet / replies / thread / related discussion -> summarize dominant emotion and disagreement -> write research notes into Obsidian`

It is **not**:

- an auto-posting tool
- a final content judge
- a one-click content machine

It **is**:

- a topic radar
- a reply / disagreement mining tool
- a research assistant for human operators

### What It Already Does

- `doctor` command to inspect resolved `obsidian_root` and `sqlite_db`
- `run-v2` command for the full workflow
- supports `AttentionVC` or `XHunt + twscrape` for discovery and source hydration
- reply / thread / related-discussion enrichment
- up to `100` reply samples per topic
- keep up to `10` comments for output by default
- no hard min-view / min-like filtering by default for final comments
- topic notes with:
  - dominant emotion
  - emotion distribution
  - primary tension
  - top comments
  - comments grouped by emotion
- writes into `00_今日雷达 / 01_主题参考 / 02_可借用观点`
- local SQLite state for `last_seen_attention_v2_ids`
- optional OpenAI-compatible writer integration

### Install

Requirements:

- `Python >= 3.14`
- either:
  - a working `AttentionVC API key`
  - or a prepared `twscrape` account pool / cookies
- an `Obsidian` path you want to write into

Recommended setup:

```bash
git clone https://github.com/xiaoxianjie341-coder/x-sentiment-radar.git
cd x-sentiment-radar
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

After install, use:

```bash
twitter-ops-agent doctor
twitter-ops-agent run-v2
```

If your local browser session is already configured and you want the free `XHunt + browser-session` path directly, you can also run:

```bash
./scripts/run-xhunt-free.sh
```

### First-Time Config

Copy the example config:

```bash
cp config/settings.example.toml config/settings.toml
```

At minimum, set:

```toml
obsidian_vault = "/absolute/path/to/Obsidian Vault"
obsidian_root = "/absolute/path/to/Obsidian Vault/推特运营Agent"

sqlite_db = "/absolute/path/to/your/sqlite.sqlite3"
```

Recommended free low-risk mode:

```toml
twscrape_db = "data/twscrape/accounts.db"
twscrape_search_enabled = false

xhunt_groups = ["cn", "global"]
xhunt_hours = 24
xhunt_limit = 15
xhunt_min_views = 1000
xhunt_min_likes = 10

attentionvc_tweet_min_views = 500
attentionvc_tweet_min_likes = 10

attentionvc_reply_sample_limit = 100
attentionvc_top_signal_count = 10
```

If you want the paid path instead, also set:

```toml
attentionvc_api_key = "avc_..."
attentionvc_base_url = "https://api.attentionvc.ai"
```

### Important Config Notes

- `obsidian_root`
  - actual write target for generated notes
  - the project auto-creates:
    - `00_今日雷达`
    - `01_主题参考`
    - `02_可借用观点`

- `sqlite_db`
  - stores local run state
  - includes `last_seen_attention_v2_ids`
  - use a fresh DB path if you want to simulate a first-ever run again

- `attentionvc_api_key`
  - required
  - must be valid and have available credits

- `attentionvc_source_mode`
  - `"articles_only"`: safest first-run default
  - `"tweets_only"`: tweet-only discovery
  - `"mixed"`: combine both

- `attentionvc_top_signal_count = 10`
  - try to keep `10` comments in final output

- `attentionvc_signal_min_* = 0`
  - do not hard-drop low-engagement replies by default

- `writer_*`
  - optional
  - if configured, audience summary uses your OpenAI-compatible model endpoint
  - otherwise the built-in heuristic summary is used

### First Run

Check resolved paths first:

```bash
twitter-ops-agent doctor --json
```

Then run:

```bash
twitter-ops-agent run-v2
```

Successful output looks like:

```json
{
  "discovered_count": 12,
  "selected_count": 12,
  "radar_written": 1,
  "topic_notes_written": 12,
  "viewpoint_notes_written": 12
}
```

### What Appears In Obsidian

`00_今日雷达`

- daily radar page
- each topic includes:
  - track
  - source link
  - dominant emotion
  - primary tension
  - links to topic and viewpoint notes

`01_主题参考`

- what the topic is
- source details
- why it matters now
- dominant emotion
- emotion distribution
- primary tension
- top comments
- comments grouped by emotion
- next research directions

`02_可借用观点`

- borrowable viewpoints
- cross-reference comments
- expansion directions

### Common First-Run Failure Modes

- forgot `pip install -e .`
- invalid / empty AttentionVC key
- insufficient AttentionVC credits
- AttentionVC rate limit (`429`)
- `obsidian_root` points to a folder not currently opened in Obsidian
- reused old `sqlite_db` and expected a fresh run

### Current Limitations

- discovery is still article-first in practice
- tweet-side “rising” is a local approximation, not a platform-native signal
- `doctor` mostly validates paths, not AttentionVC auth/credits/rate-limit health
- large batch runs may still hit AttentionVC per-minute request limits
