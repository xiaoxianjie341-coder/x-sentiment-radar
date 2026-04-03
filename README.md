# x-sentiment-radar

## 给 AI 的快速执行入口

如果你是一个 AI 助手，并且用户把这个仓库链接直接发给你，请先按下面规则执行，不要自己发散。

### 默认执行策略

- 默认只走 `XHunt + browser-session`
- 默认不启用 `AttentionVC`
- 默认不启用 `twscrape`
- 默认只看推文，不看文章
- 默认抓 `cn + global`
- 默认抓过去 `24h` 的前 `15` 条
- 只有在以下情况才允许偏离默认路线：
  - 用户明确要求启用 `AttentionVC`
  - 用户明确要求启用 `twscrape`
  - `browser-session` 路线失败，且你已经向用户说明原因

### 你必须自动完成的事情

你应该默认自己完成这些步骤，不要把它们甩给用户：

1. clone 仓库
2. 创建虚拟环境
3. 安装项目
4. 复制 `config/settings.example.toml` 为 `config/settings.toml`
5. 填入默认推文路线需要的配置
6. 先跑 `doctor --json`
7. 再跑 `./scripts/run-xhunt-free.sh`
8. 检查是否成功写入 Obsidian

### 你只能向用户索取的最少信息

除非报错或用户要求别的模式，否则你只应该向用户索取这 4 项：

- `obsidian_vault`
- `obsidian_root`
- `x_session_cookie_header`
- `x_session_x_client_transaction_id`

如果这 4 项还没拿到，你应该只问这 4 项，不要顺手再问 `AttentionVC`、`twscrape`、代理、文章源之类的问题。

### 成功标准

你完成后，至少要验证这些结果：

- `doctor --json` 输出的 `obsidian_root` 和 `sqlite_db` 符合用户预期
- `./scripts/run-xhunt-free.sh` 成功返回 JSON
- Obsidian 目录里出现：
  - `00_今日雷达`
  - `01_主题参考`
  - `02_可借用观点`
- `00_今日雷达` 里的当天日报包含：
  - `## 中文版`
  - `## 英文版`

### 复制给 AI 的提示词模板

用户可以把下面这段话直接复制给任何 AI：

```text
请把这个 GitHub 项目按 README 里的“给 AI 的快速执行入口”来完整配置并运行。严格遵守以下规则：

1. 默认只走 XHunt + browser-session。
2. 默认不要启用 AttentionVC。
3. 默认不要启用 twscrape。
4. 默认只看推文，不看文章。
5. 默认抓 cn + global，时间窗口 24h，前 15 条。
6. 除非真的必要，否则不要让我人工介入。
7. 你只能向我索取这 4 项：obsidian_vault、obsidian_root、x_session_cookie_header、x_session_x_client_transaction_id。
8. 其余步骤你自己完成：clone、建虚拟环境、安装、复制配置、运行 doctor、运行脚本、验证 Obsidian 输出。
9. 完成后请明确告诉我：实际写入路径、运行结果 JSON、以及 Obsidian 里生成了哪些文件。

如果 browser-session 路线失败，先解释失败原因，再问我要不要退回高级方案；不要默认切到 AttentionVC 或 twscrape。
```

### AI 执行清单

如果你是 AI，请按这个顺序执行：

```bash
git clone <repo-url>
cd x-sentiment-radar
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
cp config/settings.example.toml config/settings.toml
```

然后把 `config/settings.toml` 至少填成：

```toml
obsidian_vault = "/用户提供的 Obsidian Vault"
obsidian_root = "/用户提供的 Obsidian 输出目录"
sqlite_db = "/你为这次运行选择的新 sqlite 路径"

attentionvc_api_key = ""

x_session_cookie_header = "用户提供的 X 登录 cookies"
x_session_x_client_transaction_id = "用户提供的 x-client-transaction-id"
```

保留这些默认值不动：

```toml
xhunt_groups = ["cn", "global"]
xhunt_hours = 24
xhunt_limit = 15
```

然后执行：

```bash
twitter-ops-agent doctor --json
./scripts/run-xhunt-free.sh
```

如果成功，再去检查 `obsidian_root` 下是否生成当天的 `00_今日雷达`、`01_主题参考`、`02_可借用观点`。

---

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
- 新用户默认只需要一个可用的 `X` 登录态
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

如果你已经配好了本地浏览器会话，推荐直接跑免费的 `XHunt + browser-session` 链路：

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

如果你不想配 `AttentionVC`，只想看推文，最小可用配置就是再补这 3 行：

```toml
attentionvc_api_key = ""

x_session_cookie_header = "你的 X 登录 cookies"
x_session_x_client_transaction_id = "你的 x-client-transaction-id"
```

这时系统会直接走 `XHunt + browser-session`：

- 只看推文，不看文章
- 默认同时抓 `cn + global`
- 默认抓过去 `24h` 的前 `15` 条
- 跑完直接写进 Obsidian

完整的免费推文模式推荐配置如下：

```toml
attentionvc_api_key = ""

xhunt_groups = ["cn", "global"]
xhunt_hours = 24
xhunt_limit = 15
xhunt_min_views = 1000
xhunt_min_likes = 10

x_session_cookie_header = "你的 X 登录 cookies"
x_session_x_client_transaction_id = "你的 x-client-transaction-id"

attentionvc_tweet_min_views = 500
attentionvc_tweet_min_likes = 10
attentionvc_reply_sample_limit = 100
attentionvc_top_signal_count = 10
```

如果你想继续用付费模式、补文章源，再额外配：

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

- `x_session_cookie_header`
  - 你的 X 登录 cookies
  - 这是“只看推文”路线的关键配置

- `x_session_x_client_transaction_id`
  - 浏览器请求里对应的 transaction id
  - 配好它后，系统会优先走 `browser-session`，不依赖 `twscrape`

- `xhunt_*`
  - 免费推文路线的发现入口
  - 默认会同时抓 `cn + global` 两个榜单
  - 每个榜单都会取过去 `24h` 的前 `15` 条

- `attentionvc_source_mode`
  - 这是 `AttentionVC` 专用配置
  - `"articles_only"`：只抓文章型主题。第一次使用最稳
  - `"tweets_only"`：只抓普通 tweet
  - `"mixed"`：两边都抓

- `attentionvc_use_rising`
  - 是否使用 rising 文章入口
  - 当前默认推荐打开
  - 这同样只对 `AttentionVC` 生效

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
./scripts/run-xhunt-free.sh
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
  - 留空后会优先尝试 `XHunt + browser-session`
  - 没 credits 会返回 `402`
  - 请求太密会返回 `429`

- 没配 `x_session_cookie_header` / `x_session_x_client_transaction_id`
  - 这时就无法走最简单的推文路线
  - 如果同时也没有可用的 `twscrape` 账号池，就会直接报错

- `obsidian_root` 配到了一个你当前 Obsidian 没打开的目录
  - 文件其实已经写到磁盘上了
  - 但如果那个目录不是你当前打开的 vault，你不会在 Obsidian 侧边栏里直接看到

- 复跑时没换 `sqlite_db`
  - 由于 `last_seen_attention_v2_ids` 已经存在，第二次不一定会再出同样主题

### 当前限制

- `XHunt` 目前走的是公共页面解析，不是官方 API
- `browser-session` 依赖你本地 X 登录态持续有效
- tweet 侧“正在起势”不是平台现成信号，而是本地排序近似
- `doctor` 目前主要检查路径，不会提前帮你验证 `AttentionVC` credits、cookies 或浏览器会话健康
- 大批量跑时可能会撞到 `AttentionVC`、X 或 `twscrape` 的各自限制

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
- for the default beginner path, just a working logged-in `X` browser session
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

If your local browser session is configured, this is the recommended beginner path:

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

If you do not want `AttentionVC` and only want tweet-based discovery, the real minimum is:

```toml
attentionvc_api_key = ""

x_session_cookie_header = "your logged-in X cookies"
x_session_x_client_transaction_id = "your x-client-transaction-id"
```

That makes the app use `XHunt + browser-session`:

- tweet-only workflow
- default `cn + global`
- default last `24h`
- default top `15`

Recommended full free tweet mode:

```toml
attentionvc_api_key = ""

xhunt_groups = ["cn", "global"]
xhunt_hours = 24
xhunt_limit = 15
xhunt_min_views = 1000
xhunt_min_likes = 10

x_session_cookie_header = "your logged-in X cookies"
x_session_x_client_transaction_id = "your x-client-transaction-id"

attentionvc_tweet_min_views = 500
attentionvc_tweet_min_likes = 10

attentionvc_reply_sample_limit = 100
attentionvc_top_signal_count = 10
```

If you want the paid article path too, also set:

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

- `x_session_cookie_header`
  - your logged-in X cookies
  - this is the key setting for the beginner tweet-only path

- `x_session_x_client_transaction_id`
  - browser request transaction id
  - once set, the app can prefer `browser-session` instead of `twscrape`

- `xhunt_*`
  - discovery settings for the free tweet path
  - by default it pulls both `cn` and `global`
  - by default it uses the last `24h` and takes the top `15`

- `attentionvc_source_mode`
  - AttentionVC-only setting
  - `"articles_only"`: safest first-run default
  - `"tweets_only"`: tweet-only discovery
  - `"mixed"`: combine both

- `attentionvc_api_key`
  - optional
  - only needed if you want the paid article-based discovery path

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
./scripts/run-xhunt-free.sh
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
- missing `x_session_cookie_header` / `x_session_x_client_transaction_id`
- invalid / expired X browser session
- invalid AttentionVC key, if you chose the paid path
- `obsidian_root` points to a folder not currently opened in Obsidian
- reused old `sqlite_db` and expected a fresh run

### Current Limitations

- the beginner path depends on a valid local browser session
- tweet-side “rising” is a local approximation, not a platform-native signal
- `doctor` mostly validates paths, not AttentionVC auth or browser-session health
- large batch runs may still hit AttentionVC, X, or twscrape limits
