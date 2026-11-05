# DeepTutor 功能与工程取舍核查

## 用户设想与现有 DeepTutor 有多少重合

### Takeaway
截至 2026-11-04 检索到的官方资料，用户设想的大部分基础能力已经有相近实现。项目仍有工程学习和个人作品价值，但“PDF 变课程、只生成第一章、多媒体讲解、进度记忆”本身不宜被包装为新功能。此次仅阅读文档与若干 main 分支源码，没有安装、运行或验证整套应用。

### Cited Findings
- **官方文档功能**：Books 支持选择资料、审阅章节大纲、选择允许的内容类型、查看按章成本估算，并选择生成全部章节或只生成第一章；其页面可包含测验、动画与 HTML 交互组件，支持源文件指纹变化提示。——[Books 文档](https://docs.deeptutor.info/explore/book/)
- **已检查数据模型**：`book/models.py` 将内容表示为独立类型块，包括 text、figure、interactive、animation、code；章节保存学习目标、前置章节和 `source_anchors`。这说明其结构化内容设计确实进入代码，但结构字段的存在不等于内容已被事实核验。——[Book models](https://github.com/HKUDS/DeepTutor/blob/main/deeptutor/book/models.py)
- **已检查进度策略**：`learning/policy.py` 将系统评估通过与学习者主动声明掌握区分记录；后者可以推进路线。不能把它描述为完全不可跳过的硬性闯关。`mastery.py` 用近期加权正确率及少量回答时的置信上限计分。——[学习策略](https://github.com/HKUDS/DeepTutor/blob/main/deeptutor/learning/policy.py)、[掌握度计算](https://github.com/HKUDS/DeepTutor/blob/main/deeptutor/learning/mastery.py)
- **已检查代码生成边界**：`book/blocks/code.py` 生成代码与解释，Python/JSON 做语法解析；此生成器明确不执行生成代码。因此不能仅凭有 Code block 就认定示例已经运行正确或等同完整代码练习沙箱。——[CodeGenerator](https://github.com/HKUDS/DeepTutor/blob/main/deeptutor/book/blocks/code.py)

### Inferences
- 与用户最贴近的基线是 Books 加学习记录，Mastery Path 可借鉴其证据模型；不必照搬其默认教学节奏。用户明确要求自行决定下一章，应把“读到哪里”和“理解证据”保留为不同字段。
- 可竞争的个人体验方向是：打开即可接着学、困惑定位准确、换一种解释确实能解决问题、生成等待少、状态可靠。需要实测，不能声称 DeepTutor 没有这些能力。

### Gaps
- 没有在用户这份 313 页 PDF 上实测解析质量、首章时间、模型费用或讲解效果。
- 官方站有 dev 安装说明；本次部分目录页为较早抓取，源码页也来自 main 动态链接。交付可复现对比时应固定 release 或 commit。

## 哪些实现最值得借鉴

### Takeaway
优先借鉴内容块协议、课程状态、可恢复生成、可核查记忆及模块依赖边界；这些比复制整套功能菜单更适合有限时间的项目。

### Cited Findings
- **已检查生成编排**：`BookEngine` 维护按书的后台队列与正在运行页的表，同一页并发请求加入同一次生成；连续提供方故障会暂停，恢复时保留已有页。事件流归属于书而非发起请求。——[BookEngine](https://github.com/HKUDS/DeepTutor/blob/main/deeptutor/book/engine.py)
- **已检查增量保存**：`BookCompiler` 把计划页面、选择块生成器、每块保存、发送事件及汇总部分失败状态分开；其编译器与顶层编排器分离。——[BookCompiler](https://github.com/HKUDS/DeepTutor/blob/main/deeptutor/book/compiler.py)
- **已检查架构约束文件**：`.importlinter` 禁止 core 依赖 app/api/runtime/services，并限制运行时、业务服务反向导入 API。它提供了“低耦合如何由规则检查”这一具体范例；本次未执行这些检查。——[模块依赖契约](https://github.com/HKUDS/DeepTutor/blob/main/.importlinter)
- **官方记忆说明**：Memory 分为工作区原始实体、分表面摘要、跨表面归纳，可查看引用与整理预算；文档明确 L3 引用往往仅到 L2 表面，不能当作逐项事实的精确证据链。——[Memory 文档](https://docs.deeptutor.info/explore/memory/)
- **已检查互动与动画实现**：HTML 互动块经可视化 pipeline 生成，再做本地校验，交由隔离 iframe 呈现；Manim 动画另需 LaTeX、ffmpeg 等可选依赖。两种输出的开发和运维负担明显不同。——[InteractiveGenerator](https://github.com/HKUDS/DeepTutor/blob/main/deeptutor/book/blocks/interactive.py)、[AnimationGenerator](https://github.com/HKUDS/DeepTutor/blob/main/deeptutor/book/blocks/animation.py)
- 仓库采用 Apache-2.0 许可证。——[LICENSE](https://github.com/HKUDS/DeepTutor/blob/main/LICENSE)

### Inferences
- 用户仅有 2–3 周、主要熟悉 Java+Vue，建议保留熟悉的 Vue，仅用 Python 编写必要的 Agent 后端；研究接口和状态设计比整体迁移 Next.js 系统更合适。此为项目取舍判断，不是已测工期承诺。
- 首版“记忆”可用明确的课程记录：当前节、阅读位置、用户完成标记、未解决问题、已尝试讲法、可核对的练习记录。自动总结作为辅助手段；课程进度由确定性存储负责。复杂的三层个性化记忆和可视化记忆图延后。
- 内容生成默认只准备当前学习单元；按用户动作准备下一单元。增量保存、失败只重试当前块、给出可继续阅读的讲解，有直接体验价值。
- 互动首版可以先提供少量可参数化的图解/逐步演示组件，让 Agent 根据概念选择组件和填充内容；它仍可响应“我不懂”，同时把任意动画生成的验证范围缩小。要如实说明这是模板与生成内容组合。

### Gaps
- 尚未全面检查前端 iframe 隔离、全局代码执行服务、提示注入防护；不能给整体安全背书。
- 仅检视若干核心文件，不能推断整个仓库都满足低耦合或所有恢复路径都正确。

## 在两三周内是否值得做，以及怎样证明价值

### Takeaway
值得做一个自己能够解释、可反复演示的窄范围学习 Agent；不建议在同一周期复刻完整 DeepTutor。直接使用/部署开源软件最省个人学习时间，自己实现小核心更适合展示原创工程决策；两者应以实际使用和个人贡献边界比较。

### Cited Findings
- DeepTutor 当前 README 已包含 Python 与 Next.js 技术栈以及多个学习、研究、可视化工作流，系统范围远超过一个两三周个人演示。——[README](https://github.com/HKUDS/DeepTutor)
- 官方 `examples/memory_evaluation` 明确其样例使用手工合成快照，验证评测接口，不验证 L1→L2→L3 自动整理质量；默认预检查没有模型调用，答案分数为空。可借鉴其防评测泄漏、统一预算和错误计入分母的方法，不能把目录存在当作记忆效果已获证实。——[记忆评测说明](https://github.com/HKUDS/DeepTutor/blob/main/examples/memory_evaluation/README.md)
- DeepTutor 论文介绍 TutorBench 和基于画像的 LLM 学生模拟评测，并报告个性化指标提升；这是作者研究中的评测结果，不能直接换算成真人知识保留提升，也不能替代当前项目的真实用户测量。——[DeepTutor 论文](https://arxiv.org/abs/2604.26962)

### Inferences
- **本期投入值得**：PDF 解析保留页码、清晰大纲、前 1–2 章按需内容、课内追问、用户手动推进、刷新后继续、对困惑选择重新解释/例子/图解、生成状态及失败恢复、少量可回放评测。
- **本期只做简版**：日任务只需“继续当前节＋可选复习”；前置知识只记录依赖并允许“补一下这个基础”；记忆可查看并更正，不建设知识图谱平台。
- **本期不优先**：广泛自主论文搜索、通用主题课程生成、多 Agent 群体协作、语音陪伴、视频渲染链、多账号社交、完整代码 IDE、学习积分、复杂长期知识追踪。它们增加边界和调试成本，且尚未证明是用户第一痛点。
- **可展示证据**：保存一组课程定位/跨日恢复/用户纠正/无资料拒答的案例；同一困惑比较普通重复解释与策略选择后的回答，记录用户是否能独立解释或完成新例题；记录生成失败率、引用正确性、首次可学习等待和每节成本。单人试用结果应标为探索性，不宣称普适教育效果。
- Fork 适合快速使用现有能力或做一个边界明确、可贡献上游的功能；若以个人作品为主，优先复用解析、检索、渲染等成熟组件，自己实现课程状态与教学策略核心。面试价值来自能解释具体取舍、失败案例和改进证据，无法保证招聘结果。

### Gaps
- 未获得用户每周可投入小时数、模型预算、具体岗位 JD；对工期和面试适配只能提供相对取舍。
- 未运行 DeepTutor 作基线，建议后续选同一 PDF、同一模型及同样的问题进行实测，再宣称任何优势。
