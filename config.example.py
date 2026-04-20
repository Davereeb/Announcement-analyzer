# ==========================================
# 用户配置区 —— 只需修改这里
# 使用方法：复制本文件，重命名为 config.py，然后填入你的 API Key
# ==========================================

# 输入Excel路径（把文件放在项目文件夹里，填文件名即可）
INPUT_EXCEL = "你的公告数据.xlsx"

# 输出路径
OUTPUT_DB    = "announcements.db"
OUTPUT_EXCEL = "results.xlsx"

# LLM配置（选一个填入，另一个留空）
LLM_PROVIDER = "deepseek"   # 或 "qwen"

# DeepSeek 配置（推荐，性价比高）
# 申请地址：https://platform.deepseek.com/
DEEPSEEK_API_KEY  = "sk-your-deepseek-api-key-here"
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL    = "deepseek-chat"

# Qwen 配置（备用）
# 申请地址：https://dashscope.aliyuncs.com/
QWEN_API_KEY      = "sk-your-qwen-api-key-here"
QWEN_BASE_URL     = "https://dashscope.aliyuncs.com/compatible-mode/v1"
QWEN_MODEL        = "qwen-plus"   # qwen-plus 性价比高；质量要求更高可改为 qwen-max

# 性能配置
CONCURRENCY       = 20       # 并发数，建议10-30，太高会触发限流
PDF_TIMEOUT       = 30       # PDF下载超时（秒）
LLM_TIMEOUT       = 60       # LLM调用超时（秒）
MAX_RETRIES       = 3        # 失败最多重试次数
RETRY_DELAY       = 2        # 重试间隔（秒）

# 文本分类阈值（字数）
SHORT_THRESHOLD   = 3000     # 低于此字数：全文送LLM
LONG_THRESHOLD    = 10000    # 高于此字数：分章节智能抽取
