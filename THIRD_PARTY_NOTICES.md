# 开源依赖与借鉴

本项目采用成熟库，未复制 DeepTutor 的业务模块。当前没有做过与 DeepTutor 的运行效果对照，不能声称效果优于它。

| 项目 | 用途 | 许可证 |
| --- | --- | --- |
| [DeepTutor](https://github.com/HKUDS/DeepTutor) | 参考结构化内容块、按需章节生成和持久化设计 | Apache-2.0；未移植源码 |
| [FastAPI](https://github.com/fastapi/fastapi) | HTTP API | MIT |
| [Pydantic](https://github.com/pydantic/pydantic) | 输出结构校验 | MIT |
| [pypdf](https://github.com/py-pdf/pypdf) | 文本、目录与页码提取 | BSD-3-Clause |
| [rank-bm25](https://github.com/dorianbrown/rank_bm25) | 关键词检索 | Apache-2.0 |
| [jieba](https://github.com/fxsjy/jieba) | 中文分词 | MIT |
| [Vue](https://github.com/vuejs/core) / [Vite](https://github.com/vitejs/vite) | 页面与构建工具 | MIT |
| [Lucide](https://github.com/lucide-icons/lucide) | 图标 | ISC；部分图标见依赖附带许可 |
| [Marked](https://github.com/markedjs/marked) | Markdown 显示 | MIT |
| [DOMPurify](https://github.com/cure53/DOMPurify) | 富文本清理 | Apache-2.0 或 MPL-2.0 |

准确版本保存在 `server/requirements-lock.txt` 和 `web/package-lock.json`。完整依赖及许可证以安装包随附的 LICENSE / 元数据为准；发布二进制或打包分发前应汇总所有直接和间接依赖的许可文本。

用户上传的 PDF 不属于项目源码，不随仓库分发；`data/` 已排除在 Git 之外。内置体验课程为本项目编写，不冒充上传教材或实时模型生成结果。
