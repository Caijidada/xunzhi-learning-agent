# DeepTutor 之外的开源参照与功能投入判断

## 其他项目已经做到什么，哪些证据可信？

### Takeaway
“PDF＋问答＋图解＋学习记忆”已有多种实现。对 2–3 周、Java/Vue 基础、愿意学习 Python 的个人项目，借鉴具体体验与接口，比移植整个应用更合适。以下核查为官方文档与部分源码阅读，未安装、执行或测量项目；“存在代码”不代表功能已经可靠。

### Cited Findings
- **OpenTutor（官方功能声明）**：本地单用户 beta，提供课程材料导入、带出处的导师问答、练习与计划；技术栈包括 FastAPI、SQLite、Next.js/React，许可证 MIT。文档也明确高级自主流程与图谱仍有实验性质。——[官方仓库](https://github.com/zijinz456/OpenTutor)
- **OpenTutor（已查源码）**：`guided_session.py` 中 `pause_session`/`resume_session` 通过 KV 存储恢复会话状态；`tutor_notes.py` 按用户和课程保存辅导笔记，并按轮次或时间限制更新频率。更新失败时保留旧笔记。——[会话状态源码](https://github.com/zijinz456/OpenTutor/blob/main/apps/api/services/agent/guided_session.py)、[辅导笔记源码](https://github.com/zijinz456/OpenTutor/blob/main/apps/api/services/agent/tutor_notes.py)
- **OpenTutor（已查源码）**：教学策略提取涵盖有效解释、常见错误、参与方式与难度校准；每次最多提取少量策略，去重并保存。策略效果通过提取前后掌握分的变化调整置信度。代码计算的是课程中的掌握分时间序列，不能把它解释为某策略带来学习提升的因果证据。——[策略库源码](https://github.com/zijinz456/OpenTutor/blob/main/apps/api/services/agent/teaching_strategies.py)
- **OpenTutor（设计文档）**：采用可组合界面块与预设布局，拒绝复杂的完全自由拖拽；其单用户版本用 SQLite 降低部署负担。文档中的行为信号“认知负荷”检测属于作者的设计选择，不是本次验证过的心理测量。——[架构决策](https://github.com/zijinz456/OpenTutor/blob/main/docs/architecture-decisions.md)
- **Learn-With-AI（官方功能声明）**：支持材料导入、知识地图、逐知识点讲解、原文引用、选中文本 Ask AI、图解/交互 HTML、笔记和讲给老师听。采用 Go 后端与 React 前端，MIT 许可。官方说明展示图中部分学习内容是人工编排样例，实际效果依赖模型；本次未读到其对应实现源码。——[官方仓库](https://github.com/porridgeowefish/Learn-With-AI)、[产品说明及演示边界](https://porridgeowefish.github.io/Learn-With-AI/en/)

### Inferences
- 这些项目适合作为体验基线；不宜在简历中宣称“首次把 PDF 变成互动课程”。能证明的新增工作应明确到：如何定位困惑、选择呈现方式、恢复学习状态、检查生成内容、评估策略。
- 用户熟悉 Vue，直接 fork OpenTutor 或 Learn-With-AI 会同时引入不熟悉的前端和大量已有业务逻辑。短期独立实现小范围核心流程、复用成熟组件，更容易讲清自己负责的工程。
- 如果用户的目标仅为尽快学习，先使用现成产品成本更低；开发价值来自亲手设计并评估自己的核心流程。需要诚实标注借鉴、复用、原创部分。

### Gaps
- 未实测上述项目的解析质量、引用正确率、恢复可靠性、中文教学效果或真实学习收益；不能据 README 宣称它们“足够好”或用户项目一定更优。
- GitHub 个别目录/raw 页面抓取失败；OpenTutor 源码页部分缓存较旧，以上是可公开访问内容，不是固定 commit 的完整审计。

## 从用户体验出发，哪些改进值得先做？

### Takeaway
对这个用户，最有价值的是减少“重新开始”的负担，并让一句“没懂”产生有依据的教学动作。控制在 4 项核心体验，复习与评测嵌入其中；不增加完整课程平台的管理功能。

### Cited Findings
- 现有项目有可恢复学习会话与课程范围内的笔记存储，说明“第二天接着学”可以用明确的持久状态实现，无需一开始引入复杂记忆框架。——[OpenTutor 会话源码](https://github.com/zijinz456/OpenTutor/blob/main/apps/api/services/agent/guided_session.py)、[辅导笔记源码](https://github.com/zijinz456/OpenTutor/blob/main/apps/api/services/agent/tutor_notes.py)
- Learn-With-AI 官方描述了先修知识、解析覆盖缺口、逐知识点讲解与自由追问，支持把用户问题绑定到材料位置和当前主题；官方展示含人工样例，不能据图证明生成质量。——[官方产品说明](https://porridgeowefish.github.io/Learn-With-AI/en/)、[功能与使用边界](https://github.com/porridgeowefish/Learn-With-AI)
- OpenTutor 的高级图谱/语义复习/诊断模块有独立的实验状态与功能开关，说明这类系统有额外复杂度；“已实现/接入”与“已证明适合本用户”不同。——[实验状态表](https://github.com/zijinz456/OpenTutor/blob/main/docs/experimental-status-matrix.md)

### Inferences
以下是针对用户时间与背景的设计判断，不是项目发布的结论：

| 候选改进 | 2–3 周内建议 | 原因及实现边界 |
| --- | --- | --- |
| 一键接着学＋本次可用时间 | 必做 | 首屏显示上次停在哪、一个未解问题、本次一个目标；用户选 10/20 分钟，任务随实际进度变化。精确恢复当前知识点，结束时保留一句可编辑的续学摘要。 |
| 指着当前段落说“没懂” | 必做，作为核心演示 | 自动带上当前知识点、选中段落、已给解释；从改述/类比/分步图/可运行小例子中选一个动作，再用自愿小问题收反馈。避免用户重复粘贴背景。 |
| 有出处的课程＋解析覆盖提示 | 必做 | 可返回原文页码；显示有哪些页未识别。只备当前与下一小节，首次尽快可学；已读课程不因新的提问被整章重写。 |
| 可查看和修正的学习记录 | 必做，极简 | 至少进度、未解问题、已尝试解释及反馈。区分“看过”“自报理解”“练习验证”；每条判断带来源或时间，用户能纠正。数据库状态不能宣传成记忆研究突破。 |
| 一句话复述/一道迁移题 | 融入教学，不另做考试平台 | 自愿参与，帮助发现“看懂但不会用”；不阻止进入下一章。记录反馈供下一次讲解用。 |
| 简单先修补课卡 | 有余力再做 | 只维护少量章节先修关系，卡住时补一个前置知识；暂不自动构建大型知识图谱。 |
| 复杂图谱、行为推断疲劳、完整自适应难度模型 | 延后 | 单人短期数据不足，难验证效果，容易制造看似精确的掌握率。明确“没懂”与练习错误是更可解释的首版信号。 |
| 任意生成视频/长动画、自由布局、多导师群聊、社交积分、完整日历 | 首版不做 | 成本、延迟与验证范围扩张，不直接改善当前最关键的学习阻力。用少量可操作图解模板承接真正需要动态演示的内容。 |

### Gaps
- 未知用户每周可投入小时数与具体代码熟练度，不能承诺完整功能列表一定在 2–3 周内完成。先做一个 PDF 的少数章节，才有可控范围。
- “更容易持续学”与“掌握更多”需要本人使用记录、独立小测或少量外部试用来验证，不能由功能数量推导。

## 代码和可视化怎样复用，避免被技术栈拖慢？

### Takeaway
保留 Vue，把演示区做成少量类型明确的组件。首版可用一个分步流程图组件和一个小型 Python 运行区；由 Agent 决定何时调用、填充什么内容，同时记录理由和用户反馈。是否采用 Python 后端由整个项目取舍决定，不必为了组件迁移 React。

### Cited Findings
- JupyterLite 可嵌入其他应用，浏览器内运行 Python，支持多种交互绘图库；官方也提供嵌入 REPL 的方案。——[官方文档](https://jupyterlite.readthedocs.io/en/stable/)、[嵌入 REPL](https://jupyterlite.readthedocs.io/en/stable/quickstart/embed-repl.html)
- Pyodide 官方示例用 Web Worker 执行 Python，避免长时间运算阻塞界面；worker 与主界面通过消息沟通。——[Pyodide Worker 文档](https://pyodide.org/en/stable/usage/webworker.html)
- 浏览器运行环境不是完整服务器 Python；官方列出原生扩展、系统库、多线程/多进程与文件系统兼容性的限制。——[JupyterLite 兼容性说明](https://jupyterlite.readthedocs.io/en/stable/troubleshooting.html)
- JupyterLite 仓库许可证为 BSD 风格许可，使用需保留相应通知；OpenTutor 和 Learn-With-AI 为 MIT，直接复制代码也应保留许可。——[JupyterLite LICENSE](https://github.com/jupyterlite/jupyterlite/blob/main/LICENSE)、[OpenTutor LICENSE](https://github.com/zijinz456/OpenTutor/blob/main/LICENSE)、[Learn-With-AI LICENSE](https://github.com/porridgeowefish/Learn-With-AI/blob/main/LICENSE)

### Inferences
- 对用户的 AI Agent 教材，首版 Python 练习可限于上下文列表、工具调用状态机等纯逻辑；真实模型密钥与外部系统调用应由服务端受控适配，不能期待浏览器 Python 运行所有配套实验。
- 从 JSON 描述渲染已有 Vue 模板，比每次让模型自由写整页动画更容易验证、复用和保证流畅。可视化失败时回退到分步文字；这项失败恢复比新增多种视频格式更有工程展示价值。
- 做一个短演示：重新登录/打开 → 恢复上次问题 → 用户说“这里没懂” → Agent 查原文并选分步图 → 用户修改参数或做一次预测 → 保存本次反馈。这个流程同时展示持久化、检索、工具选择、生成校验和可观测性。
- 简历上的可测贡献可包括：固定样例中引用页码正确率、学习中断后的恢复成功率、互动组件渲染/运行成功率、诊断情境下策略选择与人工标注的一致性、延迟与模型调用成本。真实学习收益另用前后测与延迟回忆观察，勿把自打分当结论。

### Gaps
- 未核验浏览器 Python 与用户 PDF 各实验依赖的兼容性，不能承诺支持所有示例。
- 未做端到端压测与安全评审，组件复用也需要超时、取消、隔离与失败反馈等边界，首版可通过限制支持类型压低范围。
