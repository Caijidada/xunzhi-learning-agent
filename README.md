![循知 · 从一本 PDF 开始的个人学习 Agent](docs/images/cover.svg)

**循知**把你上传的教材整理成可以逐节学习的讲义。读到一半卡住了，可以选中那段话或那几行代码追问，沿引用跳回 PDF 原页；下次打开时，从上次停下的地方继续。

[本机启动](#本机启动) · [学习体验](#学习体验) · [工程实现](#工程实现) · [项目设计](docs/个人学习Agent项目文档.md)

![循知学习工作台，中央为讲义，右侧为专注倒计时和学习伙伴](docs/images/workspace.png)

## 学习体验

| 学习时刻 | 循知如何帮忙 |
| --- | --- |
| **刚打开一本书** | 提取目录，收起致谢、导读等附属内容。你选定一节后，再准备快速版或完整版；生成过的两版可以直接切换。 |
| **一句话没看懂** | 选中原段追问。导师结合选区、检索材料和近期互动，选择换个说法、举例、代码走读或交互演示。点来源可以核对原页。 |
| **等下一节生成** | 用之前的练习做复习卡，去原段查看知识点，再回到同一道题。新课就绪后，由你决定何时进入。 |
| **隔几天回来** | 查看全书进度、上次读到的位置和自己的疑问。可以回看旧回答、重做练习，把新的理解写进复习记录。 |

## 本机启动

准备 **Python 3.12** 和 **Node.js 22.12 或更高版本**。以下命令适用于 macOS 和 Linux。

```sh
git clone https://github.com/Caijidada/xunzhi-learning-agent.git
cd xunzhi-learning-agent
python3.12 -m venv .venv
.venv/bin/python -m pip install -r server/requirements-lock.txt
npm --prefix web ci
.venv/bin/python scripts/dev.py
```

打开 [本地学习空间](http://127.0.0.1:5173/)。**首次体验可以跳过密钥配置**。内置示例提供预写的课程和回答，可以先试一次选段提问、查看出处和回到原题。

<details>
<summary><strong>接入 DeepSeek，使用自己的 PDF 生成讲义</strong></summary>

在项目根目录运行 `cp .env.example .env`，在本机填写 `LLM_API_KEY`，并根据账户可用模型设置 `LLM_MODEL`。重启服务后导入文字版 PDF，选择小节并点击「开始这一节」。

课程、学习记录和任务保存在本机 `data/`。生成讲义或回答时，后端会把相关原文和对话发送给配置的模型服务。密钥只在后端读取。

</details>

## 工程实现

**Vue 3 + TypeScript** 提供学习工作台，**FastAPI + SQLite** 负责任务、讲义版本和学习记录。模型通过兼容接口接入。

| 设计问题 | 实现 |
| --- | --- |
| 如何让回答指向用户正在读的内容？ | PDF 分块保留物理页码，通过 BM25 检索相关材料；将选区单独传给导师，校验模型返回的来源 ID。[材料与检索](server/app/materials.py) |
| 长章节生成中断怎么办？ | 完整模式分批生成并保存检查点。停止后可以从已保存批次继续，快速版与完整版可分别保存阅读位置。[讲义生成](server/app/lessons.py) · [持久化](server/app/store.py) |
| 如何把模型输出变成可交互的讲义？ | 用 Pydantic 校验内容块、行号与场景结构。首次校验失败时，把具体问题交给模型修正一次。[模型适配](server/app/provider.py) · [数据结构](server/app/domain.py) |

**当前范围**为个人本机学习。代码走读展示模型标注的步骤；代码沙箱、扫描件 OCR 和从选题开始的联网研究仍待实现。引用校验能确认出处存在，讲解与原文是否一致仍需核对。

<details>
<summary><strong>运行检查与单服务启动</strong></summary>

```sh
.venv/bin/python -m pytest server/tests -q
npm --prefix web run build
.venv/bin/python -m uvicorn server.app.main:app --host 127.0.0.1 --port 8000
```

构建后可通过 [本地单服务入口](http://127.0.0.1:8000/) 使用工作台。后端测试使用临时数据库和模拟模型响应。备份本机学习数据时，先停止服务，再复制整个 `data/` 目录。

</details>

[开发进度](docs/开发进度.md) · [教学策略验收](docs/教学策略验收.md) · [开源借鉴记录](THIRD_PARTY_NOTICES.md)
