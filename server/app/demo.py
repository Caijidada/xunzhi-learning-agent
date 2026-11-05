"""Authored demo material; not represented as the user's PDF or a live model answer."""
from .store import Store

DEMO_ID = "course_demo"
DOC_ID = "document_demo"


def block(kind, title, body, source, **kwargs):
    return {"type": kind, "title": title, "body": body, "source_ids": [source], **kwargs}


def seed_demo(store: Store):
    if any(c["id"] == DEMO_ID for c in store.all("courses")):
        return
    sources = [
        {"id": "demo_source_1", "page": 0, "title": "Agent 的三个组成部分", "text": "这是项目内置的自编示例材料，不是上传 PDF 的摘录。Agent 可以通过模型、上下文和工具组成一个解决问题的循环。模型依据可见上下文选择下一步；工具负责执行具体操作；工具结果需要由程序加入后续上下文，模型才能利用它继续作答。"},
        {"id": "demo_source_2", "page": 1, "title": "一次工具调用怎样发生", "text": "这是自编示例。一次典型工具调用包含：用户提出问题；模型生成工具名称和参数；应用验证参数并执行工具；应用将工具结果加入消息列表；再次调用模型生成回答。模型请求一个动作和工具真正执行这个动作是不同的步骤。失败结果也应由程序明确处理。"},
        {"id": "demo_source_3", "page": 2, "title": "上下文和学习记忆", "text": "这是自编示例。上下文是一次调用可见的信息。长期学习记录保存跨会话需要的信息。阅读位置应可靠持久化；阅读完成、自述理解和练习结果是不同的证据。用户纠正一条记忆后，系统应更新有效记录，不再把旧结论当作事实。"},
    ]
    store.put("documents", DOC_ID, {"id": DOC_ID, "title": "从零理解 AI Agent · 体验材料", "filename": "内置示例", "pages": 3,
        "status": "ready", "missing_pages": [], "warnings": [], "outline": [], "demo": True})
    store.add_chunks(DOC_ID, sources)
    units = [
        {"id": f"demo_unit_{i+1}", "title": t, "chapter": i+1, "chapter_title": ch, "source_ids": [sources[i]["id"]], "minutes": m, "page_start": i+1, "page_end": i+1}
        for i, (t, ch, m) in enumerate([("Agent 的三个组成部分", "认识 Agent", 8), ("把一次工具调用拆开看", "工具与行动", 10), ("让学习记忆延续下去", "上下文与记忆", 8)])]
    store.create_course({"id": DEMO_ID, "title": "从零理解 AI Agent", "description": "从一个简单问题开始，理解模型、上下文与工具怎样一起工作。", "document_id": DOC_ID, "demo": True, "created": 0}, units)
    store.save_lesson(units[0]["id"], {"title": units[0]["title"], "summary": "学完这一节，你能用自己的话说明：一个 Agent 为什么需要模型、上下文和工具。", "mode": "demo", "blocks": [
        block("text", "先从一个日常问题开始", "想象你对一个助手说：**“帮我查一下明天的天气，再建议我带什么。”**\n\n它需要理解你的问题，获取实时天气，再根据结果给出建议。这几个动作连接起来，就构成了一次简单的 Agent 工作过程。", "demo_source_1"),
        block("callout", "一个好记的起点", "**Agent = 模型 + 上下文 + 工具**\n\n模型决定下一步，上下文提供当前信息，工具把需要的操作真正执行出来。", "demo_source_1"),
        block("text", "三个部分，各自负责什么？", "**模型：选择下一步。** 它判断是否需要查询天气，以及怎样向你解释结果。\n\n**上下文：当前能看见的信息。** 包括你的问题、所在城市和工具返回的天气。\n\n**工具：实际完成操作。** 天气查询接口负责获取数据，模型不会仅凭提出请求就自动拿到结果。", "demo_source_1"),
        block("diagram", "让这个过程动起来", "点击下一步，跟着信息走一遍。这个图是示意过程。", "demo_source_1", steps=[
            {"label": "提出目标", "detail": "你问：明天出门需要带伞吗？"},
            {"label": "选择工具", "detail": "模型发现缺少实时天气，请求查询指定城市的预报。"},
            {"label": "执行并返回", "detail": "应用执行天气工具，把“预计有雨”加入消息列表。"},
            {"label": "依据结果回答", "detail": "模型读到工具结果，回答：明天预计有雨，建议带伞。"}]),
        block("quiz", "停一下，想一想", "如果工具已经返回天气，但应用没有把结果交给模型，接下来会怎样？", "demo_source_1", options=["模型已经自动知道天气结果", "模型无法依据这个未提供的结果作答", "模型会直接修改工具的结果"], answer=1, explanation="模型只能利用实际提供的上下文。程序必须把工具结果传回，后续调用才能使用它。")
    ]})
    for i in (1, 2):
        store.save_lesson(units[i]["id"], {"title": units[i]["title"], "summary": "用一个可观察的过程，建立对这个概念的理解。", "mode": "demo", "blocks": [
            block("text", "本节核心", sources[i]["text"].replace("这是自编示例。", ""), sources[i]["id"]),
            block("callout", "带着一个问题学习", "试着用自己的话复述这个过程。如果有一步卡住，可以选中那段内容，告诉旁边的学习伙伴。", sources[i]["id"])
        ]})


def demo_response(intent, message):
    source = "demo_source_2"
    if intent in ("confused", "diagram") or any(w in message for w in ["为什么", "调用", "流程"]):
        return {"action": "step_diagram", "reason": "示例规则：用分步消息流解释工具结果如何传回。", "blocks": [
            block("text", "把“请求”与“执行”分开看", "可以把模型想成发出查询请求的人，工具是实际查资料的人。查完以后，资料必须传回来，发出请求的人才能依据它回答。下面按步骤看。", source),
            block("diagram", "工具结果怎样进入下一次回答", "这是一段预设示例，用来体验互动流程。", source, steps=[
                {"label": "用户消息", "detail": "用户问：明天需要带伞吗？"},
                {"label": "工具调用请求", "detail": "模型输出天气工具名称及城市参数，应用接收这个请求。"},
                {"label": "工具结果", "detail": "应用执行查询，把预报作为新的工具消息加入上下文。"},
                {"label": "再次调用模型", "detail": "现在上下文包含预报，模型才能依据它组织最终答案。"}])
        ]}
    if intent == "example":
        return {"action": "worked_example", "reason": "示例规则：用日常类比演示换一种讲法。", "blocks": [block("text", "像一次图书馆咨询", "你问馆员一本书在哪里。馆员先决定查目录，目录系统返回书架位置，馆员看到结果后再告诉你。\n\n这里的馆员对应模型，目录系统对应工具，问题和查询结果对应上下文。类比只帮助理解各部分的职责。", "demo_source_1")]}
    if intent == "practice":
        return {"action": "micro_exercise", "reason": "示例练习", "blocks": [block("quiz", "试着判断", "谁负责真正执行工具调用？", source, options=["应用程序或工具运行器", "只要模型提到工具就已经执行了"], answer=0, explanation="模型可以请求动作，应用或运行器负责校验并执行。为演示方便，此练习结果不写入正式练习证据。") ]}
    return {"action": "clarify", "reason": "离线示例无法回答任意问题", "blocks": [block("callout", "这里是示例体验", "当前还没有连接 DeepSeek，无法对这个问题进行真实推理。你可以试试“用步骤图讲讲工具调用”体验预设互动；配置密钥后，同一聊天入口会根据课程材料回答你的问题。", "demo_source_1")]}
