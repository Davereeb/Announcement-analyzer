"""Generate 4 PDF reports: Work Log (CN/EN) + Results Summary (CN/EN)"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfbase.ttfonts import TTFont
from datetime import datetime

# ── Register fonts ──────────────────────────────────────────────────────────
pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))
pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))

def cn_style(base, **kw):
    d = dict(fontName='STSong-Light', **kw)
    return ParagraphStyle(base + '_cn', parent=base_styles[base], **d)

base_styles = getSampleStyleSheet()

# Chinese styles
cn_h1   = ParagraphStyle('cn_h1',   fontName='STSong-Light', fontSize=20, leading=28, spaceAfter=10, textColor=colors.HexColor('#1F3864'), bold=True)
cn_h2   = ParagraphStyle('cn_h2',   fontName='STSong-Light', fontSize=14, leading=20, spaceAfter=6,  spaceBefore=14, textColor=colors.HexColor('#2E75B6'), bold=True)
cn_h3   = ParagraphStyle('cn_h3',   fontName='STSong-Light', fontSize=11, leading=16, spaceAfter=4,  spaceBefore=8,  textColor=colors.HexColor('#404040'), bold=True)
cn_body = ParagraphStyle('cn_body', fontName='STSong-Light', fontSize=10, leading=16, spaceAfter=4)
cn_note = ParagraphStyle('cn_note', fontName='STSong-Light', fontSize=9,  leading=14, spaceAfter=3,  textColor=colors.HexColor('#666666'))
cn_tag  = ParagraphStyle('cn_tag',  fontName='STSong-Light', fontSize=9,  leading=13, textColor=colors.HexColor('#C00000'))

# English styles
en_h1   = ParagraphStyle('en_h1',   fontName='Helvetica-Bold', fontSize=20, leading=28, spaceAfter=10, textColor=colors.HexColor('#1F3864'))
en_h2   = ParagraphStyle('en_h2',   fontName='Helvetica-Bold', fontSize=13, leading=19, spaceAfter=6,  spaceBefore=14, textColor=colors.HexColor('#2E75B6'))
en_h3   = ParagraphStyle('en_h3',   fontName='Helvetica-Bold', fontSize=10, leading=15, spaceAfter=4,  spaceBefore=8,  textColor=colors.HexColor('#404040'))
en_body = ParagraphStyle('en_body', fontName='Helvetica',      fontSize=10, leading=15, spaceAfter=4)
en_note = ParagraphStyle('en_note', fontName='Helvetica',      fontSize=9,  leading=13, spaceAfter=3,  textColor=colors.HexColor('#666666'))
en_tag  = ParagraphStyle('en_tag',  fontName='Helvetica-Bold', fontSize=9,  leading=13, textColor=colors.HexColor('#C00000'))

W, H = A4

def x(text):
    """Escape XML special chars for ReportLab Paragraph text."""
    return (text.replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;'))
TODAY = datetime.now().strftime('%Y-%m-%d')
NOW   = datetime.now().strftime('%Y-%m-%d %H:%M')

def hr(): return HRFlowable(width='100%', thickness=0.5, color=colors.HexColor('#CCCCCC'), spaceAfter=6, spaceBefore=6)
def sp(n=6): return Spacer(1, n)

def tbl(data, col_widths, header_bg=colors.HexColor('#2E75B6'), font='STSong-Light'):
    t = Table(data, colWidths=col_widths)
    style = [
        ('BACKGROUND', (0,0), (-1,0), header_bg),
        ('TEXTCOLOR',  (0,0), (-1,0), colors.white),
        ('FONTNAME',   (0,0), (-1,-1), font),
        ('FONTSIZE',   (0,0), (-1,-1), 9),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#F2F2F2')]),
        ('GRID',       (0,0), (-1,-1), 0.4, colors.HexColor('#DDDDDD')),
        ('VALIGN',     (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING',   (0,0), (-1,-1), 6),
        ('RIGHTPADDING',  (0,0), (-1,-1), 6),
        ('ALIGN',      (0,0), (-1,-1), 'LEFT'),
    ]
    t.setStyle(TableStyle(style))
    return t

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  1. WORK LOG — CHINESE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def build_worklog_cn():
    story = []

    story += [
        Paragraph('A股半导体公告情感分析系统', cn_h1),
        Paragraph('工作日志', ParagraphStyle('sub', fontName='STSong-Light', fontSize=15, textColor=colors.HexColor('#2E75B6'), spaceAfter=4)),
        Paragraph(f'生成时间：{NOW}', cn_note),
        hr(), sp(4),
    ]

    # 1 项目背景
    story.append(Paragraph('一、项目背景与目标', cn_h2))
    story.append(Paragraph(
        '本项目旨在对A股半导体板块2023-2025年共17,402条上市公司公告进行自动化批量处理，'
        '通过下载PDF全文、提取文本、调用大语言模型（LLM）完成三项核心任务：'
        '①判断公告是否含有影响股价的实质信息；②生成50-100字的核心摘要；③给出-2至+2的情感评分。'
        '最终输出SQLite数据库与带格式Excel报告，支持中断后断点续跑。', cn_body))
    story.append(sp())

    # 2 系统架构
    story.append(Paragraph('二、系统架构', cn_h2))
    story.append(Paragraph('系统由以下8个模块组成：', cn_body))
    arch = [
        ['文件', '功能说明'],
        ['config.py', '统一配置入口：API Key、并发数、超时、阈值等'],
        ['db.py', 'SQLite操作层：建表、批量写入、状态管理、断点续跑'],
        ['fetcher.py', 'PDF/文档下载与文本提取，支持多种文件格式'],
        ['llm.py', 'LLM调用封装：DeepSeek/Qwen，JSON解析，指数退避重试'],
        ['pipeline.py', '异步流水线主逻辑：并发控制、进度显示、统计输出'],
        ['exporter.py', '导出Excel：条件颜色格式、冻结行、股票名称列'],
        ['main.py', '一键启动入口，自动检测历史进度并续跑'],
        ['requirements.txt', '依赖列表'],
    ]
    story.append(tbl(arch, [3.5*cm, 12.5*cm]))
    story.append(sp(8))

    # 3 执行时间线
    story.append(Paragraph('三、执行时间线与关键事件', cn_h2))

    events = [
        ('阶段一', '需求分析与系统搭建',
         '解读用户需求文档，确认输入文件（851KB Excel，17,402条记录）已就位。'
         '完成8个模块的完整代码编写，安装依赖，验证DeepSeek API Key可用性，一次性通过所有预检。'),

        ('阶段二', '首次运行：全量失败（JS反爬虫拦截）',
         '首次执行main.py，17,400条记录全部标记为failed，Token消耗为零。'
         '排查发现：东方财富PDF服务器（pdf.dfcfw.com）对非浏览器请求返回JavaScript反爬虫挑战页面'
         '（Content-Type标注为application/pdf，但实为JS代码），pdfplumber尝试解析时抛出'
         '"No /Root object"异常。'
         '修复方案：使用Node.js执行JS挑战代码，解析出EO_Bot_Ssid和__tst_status两个Cookie，'
         '携带Cookie重新请求即可获得真实PDF（94KB）。'),

        ('阶段三', '二次运行：中途停止（DeepSeek余额不足）',
         '携带Cookie修复后重新运行，PDF下载成功，处理推进至约7,000条后突然停止。'
         '错误信息："Error code: 402 - Insufficient Balance"。'
         '原因：DeepSeek账户余额耗尽。用户充值后恢复运行。'
         '同期发现：Cookie全局缓存在高并发下存在竞争条件，多个协程同时触发JS挑战解析、'
         '互相覆盖，导致部分请求仍拿到JS页面。'
         '修复：引入asyncio.Lock，确保同一时间只有一个协程执行JS挑战解析。'),

        ('阶段四', '多轮续跑与格式兼容性修复',
         '随着处理深入，暴露出更多文件格式问题。'
         '问题①：5,080条返回ZIP格式文件（.docx，Office Open XML），pdfplumber无法解析，'
         '异常message为空字符串，导致error_msg字段为空。'
         '修复：安装python-docx，新增_extract_ooxml_text()函数，支持Word文档文本提取；'
         '增加ZIP格式XML降级解析兜底。'
         '问题②：25条返回HTML页面（服务器错误或跳转页）。'
         '修复：新增_extract_html_text()，使用html.parser过滤script/style标签后提取正文。'
         '问题③：4条为旧版.doc格式（OLE2，Office 97-2003），安装olefile进行二进制解析。'
         '问题④：3条为纯UTF-8中文文本文件，直接decode处理。'
         '问题⑤：1条RAR压缩包，标记为不支持格式跳过（单条，忽略）。'
         '问题⑥：超大PDF（20-29MB）下载超时截断。'
         '修复：将httpx从content模式改为stream流式下载，读取超时从30秒提升至120秒。'),

        ('阶段五', '空错误记录问题与最终清理',
         '发现大量failed记录的error_msg为空字符串。'
         '根因：asyncio.CancelledError在pipeline退出时被except Exception捕获，'
         'str(CancelledError())返回空字符串。这些记录实际上可以正常处理，'
         '重置为pending后再次运行即可完成。'
         '最终经过多轮迭代运行，已处理记录超过17,000条。'),

        ('阶段六', '结果导出与质量验证',
         '从已完成记录中抽取江丰电子（300666）30条样本导出Excel进行人工核验，'
         '用户确认LLM判断准确率较高，格式符合预期。'
         '同期应用户要求：在exporter.py中新增"股票名称"列（从公告标题自动提取）；'
         '额外导出"极端情感公告Top5"专项Excel（极度正面26条中取5条、极度负面60条中取5条）。'),
    ]

    for tag, title, body in events:
        row = tbl([[f'● {tag}：{title}', '']], [4*cm, 12*cm],
                  header_bg=colors.HexColor('#1F3864'))
        story.append(row)
        story.append(Paragraph(body, cn_body))
        story.append(sp(6))

    # 4 技术难点
    story.append(Paragraph('四、技术难点汇总', cn_h2))
    challenges = [
        ['难点', '根因', '解决方案'],
        ['JS反爬虫拦截', 'dfcfw服务器用JS挑战替代真实PDF返回', 'Node.js执行挑战JS，提取并缓存Cookie'],
        ['Cookie并发竞争', '多协程同时触发挑战、互相覆盖导致部分失败', 'asyncio.Lock序列化Cookie刷新逻辑'],
        ['多格式文档', '公告文件包含PDF/docx/HTML/纯文本/OLE等多种格式', '逐一识别magic bytes，分发到对应提取器'],
        ['超大PDF截断', '部分PDF达20-29MB，30秒超时不足', '流式下载 + 读取超时提升至120秒'],
        ['DeepSeek余额不足', '7,000条后API返回402错误', '用户充值后重启，断点续跑无数据损失'],
        ['CancelledError空错误', 'asyncio退出时取消任务，异常message为空', '识别规律后统一重置pending重跑'],
        ['LLM JSON解析失败', '模型偶发输出含多余字符或非标准JSON', '正则提取{}内容二次解析，失败则重试'],
    ]
    story.append(tbl(challenges, [3.2*cm, 5.5*cm, 7.3*cm]))
    story.append(sp(8))

    # 5 代码变更记录
    story.append(Paragraph('五、主要代码变更记录', cn_h2))
    changes = [
        ['文件', '变更内容'],
        ['fetcher.py', '① 新增Node.js JS挑战解析器  ② asyncio.Lock防并发覆盖  ③ 流式下载+120s超时  ④ 多格式提取：OOXML/HTML/OLE/纯文本'],
        ['exporter.py', '新增股票名称列（从公告标题自动提取）'],
        ['llm.py',      'LLM provider扩展：支持DeepSeek和Qwen切换'],
        ['db.py',       '新增announcement_texts侧表存储原始文本，保持主表查询性能'],
    ]
    story.append(tbl(changes, [3.5*cm, 12.5*cm]))

    return story

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  2. RESULTS SUMMARY — CHINESE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def build_results_cn():
    story = []

    story += [
        Paragraph('A股半导体板块公告情感分析', cn_h1),
        Paragraph('结果总结报告', ParagraphStyle('sub2', fontName='STSong-Light', fontSize=15, textColor=colors.HexColor('#2E75B6'), spaceAfter=4)),
        Paragraph(f'数据区间：2023-2025年 | 分析对象：A股半导体板块 | 报告生成：{NOW}', cn_note),
        hr(), sp(4),
    ]

    # 1 总体概览
    story.append(Paragraph('一、总体处理概览', cn_h2))
    overview = [
        ['指标', '数值', '说明'],
        ['数据总量', '17,402 条', '涵盖A股半导体板块2023-2025年全量公告'],
        ['已完成分析', '17,284 条 (99.3%)', '含PDF、docx、HTML、纯文本等多种格式'],
        ['有价值公告', '8,759 条 (50.7%)', '包含影响股价的实质信息'],
        ['无价值公告', '8,525 条 (49.3%)', '常规披露、程序性公告等'],
        ['LLM Token消耗', '37,731,314', '输入36,311,218 + 输出1,420,096'],
        ['API总费用', '约 ¥39.15', 'DeepSeek chat模型，约¥0.001/千输入Token'],
        ['平均每条耗时', '约 2-4 秒', '含PDF下载+文本提取+LLM分析全流程'],
    ]
    story.append(tbl(overview, [4.5*cm, 4.5*cm, 7*cm]))
    story.append(sp(8))

    # 2 情感分析结果
    story.append(Paragraph('二、情感分布分析', cn_h2))
    story.append(Paragraph(
        '对6,194条有价值公告进行情感评分（-2至+2），结果显示正面情感公告略多于负面，'
        '大量公告为中性信息披露。', cn_body))

    emo_data = [
        ['情感等级', '评分', '数量', '占有价值公告比例', '典型类型'],
        ['极度正面', '+2', '104',   '1.19%', '重大重组完成、业绩大幅预增、核心产品获批'],
        ['正面',     '+1', '4,219', '48.2%', '季报业绩增长、中标、回购完成、定增获批'],
        ['中性',     '0',  '2,859', '32.6%', '常规信息披露、董事会决议、资金使用说明'],
        ['负面',     '-1', '1,477', '16.9%', '业绩下滑、募投项目延期、诉讼风险提示'],
        ['极度负面', '-2', '100',   '1.14%', '营收净利双降、由盈转亏、重大亏损披露'],
    ]
    story.append(tbl(emo_data, [2.5*cm, 1.5*cm, 1.8*cm, 3.5*cm, 6.7*cm]))
    story.append(sp(6))
    story.append(Paragraph(
        '【关键洞察】极度负面公告（100条）数量与极度正面（104条）相当，负面公告总量（1,577条）'
        '占有价值公告的18%，反映出2023-2025年半导体板块部分企业面临较大经营压力，'
        '尤其体现在三季报等业绩披露节点。', cn_tag))
    story.append(sp(8))

    # 3 典型极端案例
    story.append(Paragraph('三、典型极端情感案例', cn_h2))

    story.append(Paragraph('▶ 极度正面案例（评分+2）', cn_h3))
    pos_cases = [
        ['股票', '公告摘要'],
        ['至正股份\n603991', '完成重大资产重组，置入AAMI半导体封装材料业务87.47%股权，交易作价30.69亿元，2024年备考净利润由负转正，战略转型成功。'],
        ['长川科技\n300604', '2025年Q3净利润同比增长207.60%至4.38亿元，单季营收同比+60%，盈利能力显著提升。'],
        ['金海通\n603061',   '2025年Q3归母净利润同比大增832.58%，前三季度净利润同比+178%，业绩高速增长。'],
        ['有研新材\n600206', '2025年前三季度业绩预增，归母净利润预计同比增长101%-127%，靶材业务驱动增长。'],
    ]
    story.append(tbl(pos_cases, [3*cm, 13*cm]))
    story.append(sp(6))

    story.append(Paragraph('▶ 极度负面案例（评分-2）', cn_h3))
    neg_cases = [
        ['股票', '公告摘要'],
        ['至正股份\n603991',   '2025年Q3单季营收同比下降51.14%，前三季度净亏损2,951万元，亏损同比扩大，经营陷入困境。'],
        ['至纯科技\n603690',   '2025年Q3营收同比-31.74%，归母净利润同比-61.91%，主营业务盈利能力显著恶化。'],
        ['欧莱新材\n688530',   '2025年Q3净利润-1,343万元，前三季度累计净利润-2,039万元，同比下降306.51%，存货大幅增加。'],
        ['阿石创\n300706',     '2025年Q3营收+21.8%但净利润同比暴跌126.57%，由盈转亏，经营活动现金流净额为负。'],
        ['联动科技\n301369',   '2025年Q3扣非净利润同比暴跌97.39%，单季归母净利润同比-81.08%，盈利能力几近崩溃。'],
    ]
    story.append(tbl(neg_cases, [3*cm, 13*cm]))
    story.append(sp(8))

    # 4 活跃股票
    story.append(Paragraph('四、公告数量最多的股票 TOP 10', cn_h2))
    story.append(Paragraph('以下股票在样本期内信息披露最为密集，通常对应重大融资、重组或持续性业务进展：', cn_body))
    stock_data = [
        ['排名', '股票代码', '已分析公告数', '备注'],
        ['1', '003043', '690', '信息披露最为活跃'],
        ['2', '300666 (江丰电子)', '640', '大量定增与问询函回复类公告'],
        ['3', '603690 (至纯科技)', '602', ''],
        ['4', '688401', '540', ''],
        ['5', '688535', '488', ''],
        ['6', '605358', '478', ''],
        ['7', '301297', '476', ''],
        ['8', '300604 (长川科技)', '462', '多条业绩预告与季报'],
        ['9', '688126', '458', ''],
        ['10', '002371', '436', ''],
    ]
    story.append(tbl(stock_data, [1.5*cm, 5*cm, 4*cm, 5.5*cm]))
    story.append(sp(8))

    # 5 有价值公告类型
    story.append(Paragraph('五、有价值公告的类型分布 TOP 10', cn_h2))
    story.append(Paragraph('以下公告类型被LLM判定为"有价值"的比率较高，是监测重点：', cn_body))
    type_data = [
        ['公告类型', '有价值条数', '分析说明'],
        ['其他', '648', '包含多种专项报告，需具体甄别'],
        ['保荐/核查意见', '491', '含大量定增、融资进展关键信息'],
        ['董事会决议公告', '301', '重大决策节点，经常涉及股权、融资、激励'],
        ['监事会决议公告', '301', '与董事会决议配套，信息密度高'],
        ['法律意见书', '286', '重大事项（并购、定增）的法律背书文件'],
        ['调研活动', '255', '机构调研纪要，含经营展望与核心数据'],
        ['专项说明/独立意见', '176', '独立财务顾问意见，用于重组等重大事项'],
        ['分配预案', '164', '分红、转增股本，直接影响股价'],
        ['回购进展情况', '154', '股份回购进度，反映公司对自身价值的判断'],
        ['股东减持', '144', '重要股东减持信号，通常有负面影响'],
    ]
    story.append(tbl(type_data, [4.5*cm, 3*cm, 8.5*cm]))
    story.append(sp(8))

    # 6 文件格式分布
    story.append(Paragraph('六、公告文件格式分布', cn_h2))
    story.append(Paragraph(
        '东方财富公告链接返回的文件格式多样，系统在处理过程中逐一适配：', cn_body))
    fmt_data = [
        ['文件格式', '估计数量', '处理方案'],
        ['PDF (.pdf)', '约11,000+', 'pdfplumber提取，支持长文本三段采样'],
        ['Word文档 (.docx)', '约5,080', 'python-docx + XML降级解析'],
        ['HTML页面', '约25',    'html.parser过滤标签提取正文'],
        ['旧版Word (.doc)', '约4',   'olefile解析OLE2格式'],
        ['纯文本 (UTF-8)', '约3',   '直接decode处理'],
        ['RAR压缩包', '1',      '标记为不支持，跳过'],
    ]
    story.append(tbl(fmt_data, [4*cm, 3*cm, 9*cm]))
    story.append(sp(8))

    # 7 结论
    story.append(Paragraph('七、结论与使用建议', cn_h2))
    conclusions = [
        '① 筛选效率：约49%的公告被判定为无价值（常规披露），LLM筛选大幅减少人工阅读量；',
        '② 情感分布：正面信号（+1/+2）合计4,323条（49.4%），负面信号（-1/-2）合计1,577条（18.0%），中性2,859条（32.6%）；',
        '③ 重点关注：极度负面（-2）公告100条建议优先人工复核，多集中在季报亏损和业绩大幅下滑；',
        '④ 板块风险：2025年三季报集中披露期出现明显负面集群，建议结合时间维度做进一步分析；',
        '⑤ 数据质量：LLM摘要经样本人工核验后反馈准确率较高，但建议对极端情感（±2）公告做二次确认；',
        '⑥ 后续优化：可进一步按股票代码、时间段、公告类型、情感区间做交叉筛选，输出专项分析报告。',
    ]
    for c in conclusions:
        story.append(Paragraph(c, cn_body))
    story.append(sp(4))

    return story


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  3. WORK LOG — ENGLISH
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def build_worklog_en():
    story = []
    story += [
        Paragraph('A-Share Semiconductor Announcement Sentiment Analysis System', en_h1),
        Paragraph('Work Log', ParagraphStyle('ensub', fontName='Helvetica-Bold', fontSize=15, textColor=colors.HexColor('#2E75B6'), spaceAfter=4)),
        Paragraph(f'Generated: {NOW}', en_note),
        hr(), sp(4),
    ]

    story.append(Paragraph('1. Project Background & Objectives', en_h2))
    story.append(Paragraph(
        'This project automates the full-pipeline processing of 17,402 A-share semiconductor sector '
        'announcements (2023-2025) sourced from Eastmoney (pdf.dfcfw.com). For each announcement the '
        'system: (1) downloads the source document, (2) extracts plain text, and (3) calls a large '
        'language model (LLM) to classify relevance, generate a 50-100 character summary, and assign '
        'a sentiment score from -2 to +2. Results are persisted to an SQLite database with full '
        'checkpoint/resume support, and exported to a formatted Excel file.', en_body))
    story.append(sp())

    story.append(Paragraph('2. System Architecture', en_h2))
    arch = [
        ['Module', 'Responsibility'],
        ['config.py',       'Unified configuration: API keys, concurrency, timeouts, thresholds'],
        ['db.py',           'SQLite layer: schema, bulk-insert (idempotent), status FSM, resume logic'],
        ['fetcher.py',      'Document download & text extraction, multi-format support'],
        ['llm.py',          'LLM wrapper: DeepSeek/Qwen, JSON parsing with fallback, exponential backoff'],
        ['pipeline.py',     'Async pipeline: semaphore concurrency, tqdm progress, batch statistics'],
        ['exporter.py',     'Excel export: conditional color formatting, frozen row, stock name column'],
        ['main.py',         'Entry point: progress detection, pipeline orchestration, auto export'],
        ['requirements.txt','Dependency list'],
    ]
    story.append(tbl(arch, [3.5*cm, 12.5*cm], font='Helvetica'))
    story.append(sp(8))

    story.append(Paragraph('3. Execution Timeline & Key Events', en_h2))

    events_en = [
        ('Phase 1', 'Requirements Analysis & System Build',
         'Reviewed the detailed requirements document. Confirmed the input Excel file (851 KB, 17,402 '
         'rows) was already present in the project directory. Built all 8 modules from scratch, installed '
         'dependencies, and validated the DeepSeek API key with a live test call. All pre-flight checks '
         'passed on the first attempt.'),

        ('Phase 2', 'First Run — Total Failure (JS Anti-Bot Interception)',
         'Executed main.py. All 17,400 records were marked as "failed" with zero token consumption. '
         'Root cause: the Eastmoney PDF CDN (pdf.dfcfw.com) returns a JavaScript bot-challenge page '
         'instead of the actual PDF, while falsely declaring Content-Type: application/pdf. pdfplumber '
         'then raised "No /Root object — Is this really a PDF?". '
         'Fix: intercept the JS challenge, execute it via Node.js subprocess, extract the resulting '
         'EO_Bot_Ssid and __tst_status cookies, and retry the request with those cookies to obtain the '
         'real PDF (~94 KB).'),

        ('Phase 3', 'Second Run — Mid-Run Stop (DeepSeek Insufficient Balance)',
         'After the cookie fix, PDF downloads succeeded and processing reached ~7,000 records before '
         'the pipeline stopped with "Error code: 402 - Insufficient Balance". The user recharged the '
         'DeepSeek account and processing resumed with full checkpoint continuity — no data loss. '
         'Concurrent fix also applied: a global cookie cache shared across 20 coroutines was vulnerable '
         'to a race condition where multiple coroutines simultaneously solved the JS challenge, '
         'overwriting each others results. Added an asyncio.Lock to serialise cookie refresh.'),

        ('Phase 4', 'Iterative Runs — Multi-Format Document Support',
         x('As processing continued, new file format failures emerged: '
         '(a) 5,080 records returned ZIP-format files (.docx, Office Open XML) — pdfplumber raised '
         'an empty-message exception. Fix: added python-docx extraction with XML fallback. '
         '(b) 25 records returned HTML pages (server error/redirect pages). Fix: html.parser '
         'extraction skipping <script> and <style> tags. '
         '(c) 4 records were legacy .doc format (OLE2, Office 97-2003). Fix: olefile binary parsing. '
         '(d) 3 records were plain UTF-8 text files. Fix: direct decode. '
         '(e) 1 record was a RAR archive — marked as unsupported and skipped. '
         '(f) Several 20-29 MB PDFs were being truncated due to the 30-second read timeout. '
         'Fix: switched httpx from buffered to streaming mode, raised read timeout to 120 seconds.')),

        ('Phase 5', 'Empty-Error Records & Final Cleanup',
         'A pattern of ~5,000 failed records with blank error_msg was traced to '
         'asyncio.CancelledError being caught by "except Exception as e" during pipeline shutdown — '
         'str(CancelledError()) evaluates to an empty string. Probe tests confirmed the underlying '
         'URLs were valid (PDF or docx). Resetting these to "pending" and re-running successfully '
         'processed them. Multiple cleanup passes were performed until the remaining failure count '
         'converged to a small residual.'),

        ('Phase 6', 'Output Quality Validation & Export Enhancements',
         '30 sample records for stock 300666 (Jiangfeng Electronics) were exported to Excel for '
         'manual review. The user confirmed high accuracy in valuable/non-valuable classification and '
         'summary quality. Two export enhancements were applied per user feedback: '
         '(1) Added a "Stock Name" column auto-extracted from the announcement title prefix '
         '(format: "StockName:AnnouncementContent"); '
         '(2) Generated an additional targeted "Extreme Sentiment Top-5" Excel workbook '
         '(top 5 emotion=+2 and emotion=-2 records).'),
    ]
    for tag, title, body in events_en:
        row = tbl([[f'{tag}: {title}', '']], [4*cm, 12*cm],
                  header_bg=colors.HexColor('#1F3864'), font='Helvetica')
        story.append(row)
        story.append(Paragraph(body, en_body))
        story.append(sp(6))

    story.append(Paragraph('4. Technical Challenges Summary', en_h2))
    challenges_en = [
        ['Challenge', 'Root Cause', 'Solution'],
        ['JS anti-bot interception', 'CDN serves JS challenge instead of PDF', 'Node.js JS execution; cookie caching'],
        ['Cookie concurrency race', '20 coroutines simultaneously refresh cookies', 'asyncio.Lock serialises refresh'],
        ['Multi-format documents', 'PDF/docx/HTML/text/OLE served from same CDN', 'magic-bytes dispatch to format-specific extractors'],
        ['Large PDF timeout', '20-29 MB files exceed 30s read timeout', 'Streaming mode + 120s read timeout'],
        ['DeepSeek balance 402', 'Account exhausted at ~7,000 records', 'User recharge; checkpoint resume preserves progress'],
        ['Empty CancelledError', 'asyncio shutdown cancels in-flight tasks', 'Reset blank-error records to pending; re-run'],
        ['LLM JSON parse error', 'Model occasionally outputs non-standard JSON', 'Regex extraction fallback; retry on failure'],
    ]
    story.append(tbl(challenges_en, [3.5*cm, 5*cm, 7.5*cm], font='Helvetica'))
    story.append(sp(8))

    story.append(Paragraph('5. Code Change Log', en_h2))
    changes_en = [
        ['Module', 'Changes'],
        ['fetcher.py', '(1) Node.js JS challenge solver  (2) asyncio.Lock cookie guard  (3) Streaming + 120s timeout  (4) OOXML / HTML / OLE / plaintext extractors'],
        ['exporter.py', 'Added "Stock Name" column (auto-extracted from title prefix)'],
        ['llm.py',      'Provider abstraction: DeepSeek / Qwen switchable via config'],
        ['db.py',       'Side-table announcement_texts for raw text storage; keeps main table lean'],
    ]
    story.append(tbl(changes_en, [3.5*cm, 12.5*cm], font='Helvetica'))
    return story


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  4. RESULTS SUMMARY — ENGLISH
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def build_results_en():
    story = []
    story += [
        Paragraph('A-Share Semiconductor Announcement Sentiment Analysis', en_h1),
        Paragraph('Results Summary Report', ParagraphStyle('ensub2', fontName='Helvetica-Bold', fontSize=15, textColor=colors.HexColor('#2E75B6'), spaceAfter=4)),
        Paragraph(f'Data period: 2023-2025  |  Sector: A-Share Semiconductors  |  Report date: {NOW}', en_note),
        hr(), sp(4),
    ]

    story.append(Paragraph('1. Processing Overview', en_h2))
    overview = [
        ['Metric', 'Value', 'Notes'],
        ['Total records', '17,402', 'Full A-share semiconductor announcements 2023-2025'],
        ['Records analysed', '17,284 (99.3%)', 'Includes PDF, docx, HTML, plain-text formats'],
        ['Valuable announcements', '8,759 (50.7%)', 'Contains material price-sensitive information'],
        ['Non-valuable announcements', '8,525 (49.3%)', 'Routine disclosures, procedural notices'],
        ['Total tokens consumed', '37,731,314', 'Input 36,311,218 + Output 1,420,096'],
        ['API cost', '~CNY 39.15', 'DeepSeek-chat; ~CNY 0.001 per 1K input tokens'],
        ['Avg. processing time', '~2-4 sec/record', 'End-to-end: download + extract + LLM call'],
    ]
    story.append(tbl(overview, [4.5*cm, 4.5*cm, 7*cm], font='Helvetica'))
    story.append(sp(8))

    story.append(Paragraph('2. Sentiment Distribution', en_h2))
    story.append(Paragraph(
        'Sentiment scores are assigned only to the 6,194 "valuable" announcements. '
        'Positive signals slightly outweigh negative ones, while a substantial share '
        'carries neutral sentiment (material information without a clear directional bias).', en_body))
    emo_en = [
        ['Sentiment', 'Score', 'Count', '% of Valuable', 'Typical Announcement Types'],
        ['Extremely Positive', '+2', '104',   '1.19%', 'Major M&A completion, profit surge, product approval'],
        ['Positive',           '+1', '4,219', '48.2%', 'Earnings growth, contract wins, buyback completion'],
        ['Neutral',            '0',  '2,859', '32.6%', 'Routine disclosures, board resolutions, fund usage'],
        ['Negative',           '-1', '1,477', '16.9%', 'Earnings decline, project delays, litigation risk'],
        ['Extremely Negative', '-2', '100',   '1.14%', 'Revenue & profit double-decline, turning to loss'],
    ]
    story.append(tbl(emo_en, [3*cm, 1.5*cm, 1.5*cm, 3*cm, 7*cm], font='Helvetica'))
    story.append(sp(6))
    story.append(Paragraph(
        'Key Insight: Extremely negative (100) and extremely positive (104) announcements are nearly '
        'equal. Total negative signals (1,577 records, 18.0%) reflect the significant operational '
        'pressure faced by parts of the semiconductor sector in 2023-2025, especially around quarterly '
        'earnings disclosure periods.', en_tag))
    story.append(sp(8))

    story.append(Paragraph('3. Representative Extreme-Sentiment Cases', en_h2))
    story.append(Paragraph('Top Extremely Positive (+2) Announcements', en_h3))
    pos_en = [
        ['Stock', 'Summary'],
        ['Zhizheng (603991)', 'Completed major asset restructuring — injected AAMI semiconductor packaging materials business at CNY 3.07 bn; pro-forma 2024 net profit turned positive. Strategic transformation into semiconductor packaging sector.'],
        ['Changchuan (300604)', 'Q3 2025 net profit +207.6% YoY to CNY 438 mn; revenue +60% YoY. Profitability surged as semiconductor test equipment demand accelerated.'],
        ['Jinhaitung (603061)', 'Q3 2025 net profit +832.6% YoY; 9M revenue +87.9%, net profit +178.2%. Explosive growth driven by ramp-up in semiconductor packaging equipment.'],
        ['Youyan (600206)',     '9M 2025 earnings pre-announcement: net profit expected +101%-127% YoY, driven by sputtering target sales growth and rare-earth subsidiary turning profitable.'],
    ]
    story.append(tbl(pos_en, [3.5*cm, 12.5*cm], font='Helvetica'))
    story.append(sp(6))

    story.append(Paragraph('Top Extremely Negative (-2) Announcements', en_h3))
    neg_en = [
        ['Stock', 'Summary'],
        ['Zhizheng (603991)',   'Q3 2025 quarterly revenue -51.1% YoY; 9M cumulative net loss CNY 29.5 mn, loss widening YoY. Operational deterioration despite pending restructuring.'],
        ['Zhichun Tech (603690)', 'Q3 2025 revenue -31.7% YoY, net profit -61.9% YoY. Core business profitability significantly eroded; full-year outlook worsened.'],
        ['Oulai (688530)',      'Q3 2025 net profit -CNY 13.4 mn; 9M cumulative loss -CNY 20.4 mn, -306.5% YoY. Inventory surge signals demand weakness.'],
        ['Ashichuang (300706)', 'Q3 2025 revenue +21.8% but net profit -126.6% YoY, turning to a loss. Operating cash flow turned negative.'],
        ['Liandong (301369)',   'Q3 2025 non-recurring net profit -97.4% YoY; net profit -81.1% YoY. Near-collapse of core business profitability.'],
    ]
    story.append(tbl(neg_en, [3.5*cm, 12.5*cm], font='Helvetica'))
    story.append(sp(8))

    story.append(Paragraph('4. Most Active Stocks (Top 10 by Analysed Announcements)', en_h2))
    stock_en = [
        ['Rank', 'Stock Code', 'Analysed Count', 'Note'],
        ['1', '003043',             '690', 'Most active discloser in the sample'],
        ['2', '300666 (Jiangfeng)', '640', 'Heavy rights-issue & inquiry-response filings'],
        ['3', '603690 (Zhichun)',   '602', ''],
        ['4', '688401',             '540', ''],
        ['5', '688535',             '488', ''],
        ['6', '605358',             '478', ''],
        ['7', '301297',             '476', ''],
        ['8', '300604 (Changchuan)','462', 'Multiple earnings pre-announcements'],
        ['9', '688126',             '458', ''],
        ['10', '002371',            '436', ''],
    ]
    story.append(tbl(stock_en, [1.5*cm, 5*cm, 3.5*cm, 6*cm], font='Helvetica'))
    story.append(sp(8))

    story.append(Paragraph('5. Valuable Announcement Types — Top 10', en_h2))
    type_en = [
        ['Type', 'Count', 'Significance'],
        ['Other / Miscellaneous',        '648', 'Catch-all category; requires further sub-classification'],
        ['Sponsor / Verification Opinion','491', 'Key checkpoints in equity financing processes'],
        ['Board Resolution',             '301', 'High-value decision nodes: equity, financing, incentives'],
        ['Supervisory Board Resolution', '301', 'Accompanies board resolutions; high information density'],
        ['Legal Opinion',                '286', 'Legal backing for M&A / rights issues'],
        ['Investor Relations Activity',  '255', 'Management Q&A; contains forward guidance'],
        ['Special Statement / Opinion',  '176', 'Independent financial advisor opinions for major events'],
        ['Distribution Plan',            '164', 'Dividends / bonus shares; direct price impact'],
        ['Buyback Progress',             '154', 'Signals management confidence in valuation'],
        ['Shareholder Reduction',        '144', 'Key-shareholder sell-down; typically negative signal'],
    ]
    story.append(tbl(type_en, [5*cm, 2.5*cm, 8.5*cm], font='Helvetica'))
    story.append(sp(8))

    story.append(Paragraph('6. Conclusions & Recommendations', en_h2))
    concs = [
        '1. Filtering efficiency: ~49% of announcements are classified as non-valuable, dramatically reducing manual reading workload.',
        '2. Sentiment split: Positive signals (+1/+2) account for 49.4% of valuable announcements; negative (-1/-2) 18.0%; neutral 32.6%.',
        '3. Priority review: 100 extremely negative (-2) announcements are recommended for immediate manual review — mostly quarterly loss disclosures.',
        '4. Sector risk signal: A notable cluster of negative announcements appeared during the Q3 2025 earnings season, suggesting sector-wide pressure.',
        '5. Data quality: Manual spot-checks on 30 records confirmed high LLM accuracy. Extreme sentiment (±2) records are recommended for secondary verification.',
        '6. Next steps: Cross-filter by stock code, date range, announcement type, and sentiment band to generate targeted sub-reports.',
    ]
    for c in concs:
        story.append(Paragraph(c, en_body))
    story.append(sp(4))
    return story


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  BUILD & SAVE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def build_pdf(filename, story):
    doc = SimpleDocTemplate(
        filename, pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2.2*cm, bottomMargin=2*cm,
        title=filename,
    )
    doc.build(story)
    print(f'  ✓ {filename}')


if __name__ == '__main__':
    import os
    os.chdir('/Users/davereeb./announcement_analyzer')
    print('生成 PDF 报告...')
    build_pdf('工作日志_中文版.pdf',    build_worklog_cn())
    build_pdf('Work_Log_EN.pdf',        build_worklog_en())
    build_pdf('结果总结_中文版.pdf',    build_results_cn())
    build_pdf('Results_Summary_EN.pdf', build_results_en())
    print('全部完成！')
