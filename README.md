# 循知 · 个人学习 Agent

把 PDF 变成可以逐节学习、追问、查看来源的学习工作台。首版面向个人本机使用，Python + FastAPI + Vue 3 + TypeScript，默认接入 DeepSeek。

## 目前可以做什么

- 上传文字版 PDF，保留物理页码、提取目录，建立本地分块资料库。
- 按需准备当前小节，不预生成整本书；用户手动切换章节。导读与附属内容默认收起，可根据原文优化学习路径。
- 已保存的讲解可按新策略重新生成，旧版本归档；每段提供追问与演示入口。
- 接入模型后，根据原文生成讲解、例子、分步图解和自愿练习；追问时检索相关材料并携带近期互动记录。
- 查看引用片段与 PDF 原页，选择正文片段继续问。
- 保存阅读位置、困惑、练习结果和用户自述；可以更正记录，日常任务跟随实际位置。
- 后台任务可取消、失败重试、重启后恢复已保存的内容块；记录模型调用次数、耗时和 token 使用量。

**没有密钥也能体验**：内置示例使用预先编写的课程与回答；上传材料使用原文导读。页面明确标示模式，这些不算真实模型回答。

## 本机启动

建议 Python 3.12、Node.js 22.12 或以上。首次安装：

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r server/requirements-lock.txt
npm --prefix web ci
cp .env.example .env
```

在 `.env` 填写 `LLM_API_KEY`。不要把密钥发到聊天、放入前端或提交到 Git。默认配置为：

```dotenv
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-flash
LLM_API_KEY=你的密钥
```

模型名可修改。默认值依据 2026-11-05 查阅的 [DeepSeek 官方文档](https://api-docs.deepseek.com/)；具体可用模型以账户为准。修改配置后重启服务。配置模型后，相关原文片段和对话会发送给配置的模型服务商。

```sh
.venv/bin/python scripts/dev.py
```

打开 http://127.0.0.1:5173/ 。按 Ctrl+C 同时停止前后端。当前工作区依赖已安装，可以直接运行上面的启动命令。

也可以构建后只启动 Python 服务：

```sh
npm --prefix web run build
.venv/bin/python -m uvicorn server.app.main:app --host 127.0.0.1 --port 8000
```

此时访问 http://127.0.0.1:8000/ 。接口说明位于 `/docs`。数据保存在 `data/`，重启不会清空；备份时先停止服务再复制整个目录。首版没有登录与多用户隔离，请保持监听本机地址。

## 验证

```sh
.venv/bin/python -m pytest server/tests -q
npm --prefix web run build
```

测试使用临时数据库和模拟模型响应，不消耗真实模型额度。真实 DeepSeek 质量评估仍需接入密钥后进行。来源 ID 校验仅证明引用存在，不能自动证明每句话都被来源支持。

推荐演示路径：内置课程 → 分步图解 →「还没理解」→ 来源 → 学习记忆更正 → 手动下一节 → 刷新恢复 → 上传自己的 PDF。

## 结构与边界

`server/app/materials.py` 负责解析和 BM25 检索，`provider.py` 负责模型与结构化输出，`service.py` 负责教学任务，`store.py` 负责 SQLite 持久化。前端只调用 HTTP 接口，密钥留在后端。

这是可运行的首版实现，尚未完成整个产品设计：**选题联网研究、代码运行沙箱、任意动画生成、OCR、向量检索、目录编辑及独立学习效果评测**仍待开发。当前支持步骤图及模型编排的对象、边界、信息流和状态对照场景，支持播放、拖动时间线和放大；代码块只展示；每日任务是依据进度与有效困惑记录的规则计划。长小节目前只选取前几个片段生成导读，不能宣称覆盖整节全部内容。

详见 [开发进度](docs/开发进度.md)、[项目设计](docs/个人学习Agent项目文档.md) 与 [开源借鉴记录](THIRD_PARTY_NOTICES.md)。
