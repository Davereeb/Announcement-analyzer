# A股公告情感分析系统

自动批量下载、解析 A 股上市公司公告（PDF / Word / HTML），调用大语言模型（DeepSeek / Qwen）完成**四项核心任务**：

1. **价值判断** — 判断公告是否含有影响股价的实质信息（输出：有 / 无）
2. **核心摘要** — 生成 50-100 字的精炼摘要
3. **情感评分** — 给出 -2（极度负面）到 +2（极度正面）的量化评分
4. **细粒度评分** — 估算全文中有效信息的密度（0-100%整数）

结果存入 SQLite 数据库，并导出带颜色格式的 Excel 报告。支持**断点续跑**：中途停止后重新运行，自动跳过已完成记录。

---

## 目录结构

```
announcement_analyzer/
├── config.py            # 配置文件（含API Key，本地保存，不上传）
├── config.example.py    # 配置模板（复制后重命名为 config.py）
├── main.py              # 一键启动入口
├── pipeline.py          # 异步流水线主逻辑
├── fetcher.py           # PDF/文档下载与文本提取
├── llm.py               # LLM调用封装（DeepSeek / Qwen）
├── db.py                # SQLite数据库操作层
├── exporter.py          # Excel导出（条件颜色格式）
├── generate_reports.py  # 生成PDF工作日志与结果总结
├── intro.html           # 系统框架介绍演示页（双击可直接打开）
├── chart.min.js         # 离线图表库（intro.html 依赖）
└── requirements.txt     # Python依赖列表
```

---

## 环境要求

- Python 3.10 或更高版本
- Node.js（用于绕过东方财富网站的反爬虫验证，需可在终端执行 `node` 命令）

验证方法：
```bash
python3 --version   # 应输出 Python 3.10+
node --version      # 应输出 v14+ 以上版本
```

---

## 快速开始

### 第一步：克隆项目

```bash
git clone https://github.com/Davereeb/Announcement-analyzer.git
cd Announcement-analyzer
```

### 第二步：安装依赖

```bash
pip install -r requirements.txt
```

### 第三步：配置 API Key

将 `config.example.py` 复制一份，重命名为 `config.py`：

```bash
cp config.example.py config.py
```

然后用任意文本编辑器打开 `config.py`，填入以下内容：

| 配置项 | 说明 |
|--------|------|
| `INPUT_EXCEL` | 输入Excel文件名（放在项目根目录） |
| `DEEPSEEK_API_KEY` | DeepSeek API Key，申请地址：https://platform.deepseek.com/ |
| `QWEN_API_KEY` | Qwen API Key（备用），申请地址：https://dashscope.aliyuncs.com/ |
| `LLM_PROVIDER` | 选择使用哪个模型：`"deepseek"` 或 `"qwen"` |
| `CONCURRENCY` | 并发数，默认20，如遇限流可调低至10 |

### 第四步：准备输入文件

将包含公告数据的 Excel 文件放入项目根目录，文件需包含以下列：

| 列名 | 说明 |
|------|------|
| 股票代码 | 如 `300666` |
| 发布时间 | 如 `2024-01-15` |
| 公告标题 | 如 `江丰电子:关于xxx的公告` |
| 公告类型 | 如 `业绩预告` |
| 公告链接 | 东方财富PDF直链，如 `http://pdf.dfcfw.com/pdf/...` |

然后在 `config.py` 中将 `INPUT_EXCEL` 改为你的文件名。

### 第五步：运行

```bash
python3 main.py
```

程序会显示实时进度条，每处理 100 条打印一次统计信息（有价值数量、Token 消耗、预估费用）。

**中断后续跑：** 直接再次运行 `python3 main.py`，已完成的记录会自动跳过。

---

## 输出文件

| 文件 | 说明 |
|------|------|
| `announcements.db` | SQLite数据库，存储全量处理结果和原始文本 |
| `results_YYYYMMDD_HHMMSS.xlsx` | 带格式的Excel结果报告 |

### Excel 输出列说明

| 列名 | 类型 | 说明 |
|------|------|------|
| 股票代码 / 股票名称 | string | 来自输入数据，股票名称从公告标题前缀自动提取 |
| 发布时间 / 公告标题 / 公告类型 | string | 来自输入数据 |
| is_valuable | "有" / "无" | 是否含影响股价的实质信息 |
| summary | string \| null | LLM生成的50-100字摘要；无价值时为 null |
| reason | string | LLM一句话判断依据 |
| **emotion** | int -2~+2 \| null | 情感评分；无价值时为 null；Excel 5色色阶 |
| **granularity** | int 0~100 | 信息密度估算（%）；有价值/无价值均输出；Excel 5色色阶 |
| doc_type | short/medium/long | 文本长度分档（<3000 / 3000-10000 / >10000字） |
| text_length | int | 提取后纯文本字数 |
| fetch_time / llm_time | float（秒） | 各阶段耗时 |
| input_tokens / output_tokens | int | 本条 LLM 调用的 token 消耗 |
| processed_at | datetime | 处理完成时间戳 |

### 情感评分（emotion）色阶

| Excel颜色 | 评分 | 打分标准 |
|-----------|------|----------|
| 🟢 深绿 | +2 | 净利润增幅>100%；重大重组完成；核心资质获批；回购>3%股本 |
| 🟢 浅绿 | +1 | 业绩增长10-100%；重大中标/合同；定增获批；回购进展 |
| ⬜ 白色 | 0 | 实质内容但方向不明确；小额投资；资产出售影响有限 |
| 🔴 浅红 | -1 | 业绩下滑未亏损；重要股东减持；募投项目延期 |
| 🔴 深红 | -2 | 由盈转亏；净利润暴跌>80%；重大违规/处罚；重大诉讼败诉 |

### 细粒度评分（granularity）色阶

> **定义**：`granularity = 有效信息字数 ÷ 全文字数 × 100`
>
> 「有效信息」= 对股价判断有直接参考价值的内容（关键财务数据、金额、核心结论）
> 由 LLM 在阅读文本时直接估算，输出 0-100 整数。

| Excel颜色 | 范围 | 密度等级 | 典型公告类型 |
|-----------|------|----------|-------------|
| 🟢 深绿 | 81-100% | 极高 | 季报业绩快报、重组完成简报 |
| 🟢 浅绿 | 61-80% | 高 | 季报摘要、回购完成公告 |
| 🔵 浅蓝 | 31-60% | 中等 | 半年报摘要、重大合同公告 |
| 🟡 浅黄 | 11-30% | 低 | 年度报告全文、招股说明书 |
| ⬜ 浅灰 | 0-10% | 极低 | 公司章程、股东大会通知 |

> 💡 **推荐筛选组合**：`is_valuable = 有` + `granularity ≥ 61`，快速定位价值高且信息集中的公告

---

## 长文本处理策略

超过 10,000 字的文档（年报、招股书等）采用**体感优化三段采样**送入 LLM：

```
跳过前 8%（封面/目录/免责声明）
├─ 前段正文（8%-16%位置）：2,000字  ← 关键披露/摘要区
├─ 中段正文（50%位置附近）：2,000字  ← 核心财务数据区
└─ 后段正文（80%位置附近）：2,000字  ← 结论/风险前瞻区
跳过后 7%（附录/签字页）
```

**注意**：long 文档的 `granularity` 为基于节选片段的推断值，非精确统计。

---

## 生成PDF报告（可选）

处理完成后，可运行以下命令生成中英文工作日志和结果总结（共4个PDF）：

```bash
python3 generate_reports.py
```

---

## 支持的文件格式

系统自动识别公告链接返回的文件类型，无需手动配置：

| 格式 | 识别方式 | 处理库 |
|------|----------|--------|
| PDF (`.pdf`) | magic bytes `%PDF` | pdfplumber |
| Word文档 (`.docx`) | magic bytes `PK`（ZIP格式） | python-docx + XML降级 |
| 旧版Word (`.doc`) | magic bytes `D0CF11E0` | olefile |
| HTML页面 | 开头含 `<html`/`<!DO` 等 | html.parser |
| 纯文本 (UTF-8) | UTF-8 可解码 | 直接 decode |

---

## 费用估算（DeepSeek 定价）

| 项目 | 单价 |
|------|------|
| 输入 Token | ¥0.001 / 千token |
| 输出 Token | ¥0.002 / 千token |
| 每条公告平均成本 | ≈ ¥0.002–0.004（不到半分钱） |

---

## 常见问题

**Q: 运行时报错 `node: command not found`**
A: 需要安装 Node.js。macOS 可用 `brew install node`，或前往 https://nodejs.org 下载安装。

**Q: 遇到 `402 Insufficient Balance` 错误**
A: DeepSeek 账户余额不足，充值后直接重新运行 `python3 main.py`，会自动从中断处继续，不会重复计费。

**Q: 部分记录一直失败怎么办**
A: 查看 `announcements.db` 中的 `error_msg` 字段了解失败原因。网络超时类错误可重新运行重试；`Unsupported file format` 表示该公告为不支持的格式（如 RAR 压缩包），需手动处理。

**Q: 如何只处理特定股票**
A: 在输入 Excel 中只保留目标股票的行，然后运行即可。如果数据库已有其他记录，新记录会自动追加而不影响旧记录。

**Q: granularity 字段没有数据（为 null）**
A: 该字段是在最新版本中新增的。旧版本处理的记录不含此字段，重新处理这些记录后会自动填充。

---

## 技术栈

- **异步并发**：`asyncio` + `asyncio.Semaphore`（20并发）
- **HTTP客户端**：`httpx`（流式下载，支持大文件，120s超时）
- **PDF解析**：`pdfplumber`
- **Word解析**：`python-docx`、`olefile`
- **LLM调用**：`openai` SDK（兼容 DeepSeek / Qwen 接口）
- **数据存储**：`sqlite3`（标准库）
- **Excel导出**：`openpyxl`
- **进度显示**：`tqdm`

---

## License

MIT
