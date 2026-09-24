<<<<<<< HEAD
# ai-write
=======
# AI 论文写作系统

基于**多 Agent 协作 + RAG 检索增强**的论文写作系统，覆盖「选题 → 大纲 → 分章撰写 → 文献引用 → 润色 → 质量检查」全流程。

## 技术栈

| 层 | 技术 |
| --- | --- |
| 前端 | Vue 3 + TypeScript + Vite + Pinia + Vue Router + Element Plus |
| 后端 | FastAPI + SQLAlchemy（异步） + LangChain + LangGraph |
| 向量库 | ChromaDB（本地持久化） |
| 大模型 | 千问（阿里云百炼 DashScope，OpenAI 兼容模式），也支持 OpenAI / DeepSeek / 智谱 |
| 数据库 | SQLite（开发）/ PostgreSQL（生产） |

## 项目结构

```
ai-paper-writer/
├── backend/
│   ├── app/
│   │   ├── main.py              # 应用入口
│   │   ├── config.py            # 配置（pydantic-settings）
│   │   ├── database.py          # 异步数据库会话
│   │   ├── models/              # ORM 模型（user / paper / chapter / reference）
│   │   ├── schemas/             # Pydantic 模式
│   │   ├── api/                 # 路由（auth / papers / chapters / references）
│   │   ├── agents/              # 5 个 Agent + BaseAgent
│   │   ├── workflows/           # LangGraph 工作流（state / graph_builder / paper_workflow）
│   │   ├── rag/                 # 向量化 / 向量存储 / 检索器
│   │   ├── services/            # 业务服务层
│   │   └── utils/               # LLM 工具与通用函数
│   ├── requirements.txt
│   ├── .env.example
│   └── Dockerfile
├── frontend/
│   ├── src/                     # api / components / views / stores / router / styles
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml
└── README.md
```

## 多 Agent 与工作流

- **TopicAgent**：结合领域与关键词推荐可行选题
- **OutlineAgent**：按论文类型与字数生成结构化大纲
- **WriterAgent**：逐章撰写正文，撰写前通过 RAG 检索相关文献
- **ReferenceAgent**：文献格式化（GB/T 7714 / APA / MLA）与引用编号
- **PolishAgent**：语言 / 逻辑 / 格式多角度润色
- **QualityAgent**：质量检查，不达标则回流修订

LangGraph 工作流节点：`analyze_topic →（recommend_topic | generate_outline）→ write_sections → add_references → polish_paper → quality_check`，含条件边分支。

## 快速开始

### 1. 配置 API Key（必读）

后端默认使用**千问**，需要在 `backend/.env` 中填写你的 Key：

```env
LLM_PROVIDER=qwen
QWEN_API_KEY=sk-你的千问APIKey
QWEN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
QWEN_MODEL=qwen-plus

EMBEDDING_PROVIDER=qwen
EMBEDDING_MODEL=text-embedding-v3
```

> 对话模型与向量化模型都走同一个千问 Key，可在[阿里云百炼控制台](https://bailian.console.aliyun.com/)创建。

### 2. 启动后端

```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows；macOS/Linux 用 source venv/bin/activate
pip install -r requirements.txt
copy .env.example .env         # 然后编辑 .env 填写 QWEN_API_KEY
uvicorn app.main:app --reload --port 8000
```

接口文档：http://localhost:8000/docs ，健康检查：http://localhost:8000/health

### 3. 启动前端

```bash
cd frontend
npm install
npm run dev
```

访问 http://localhost:5173

## Docker Compose 一键部署

```bash
# 先设置千问 Key（PowerShell: $env:QWEN_API_KEY="sk-xxx"）
export QWEN_API_KEY=sk-你的千问APIKey
docker compose up -d --build
```

- 前端：http://localhost:3000
- 后端：http://localhost:8000
- 数据库：PostgreSQL 15（数据持久化在 `postgres_data` 卷），向量库持久化在 `chroma_data` 卷

## 主要接口

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/api/auth/register`、`/api/auth/login` | 注册 / 登录（JWT） |
| GET | `/api/auth/me` | 当前用户 |
| GET/POST | `/api/papers/` | 论文列表 / 创建 |
| GET/PUT/DELETE | `/api/papers/{id}` | 论文详情 / 更新 / 删除 |
| POST | `/api/papers/{id}/topics` | 选题推荐 |
| POST | `/api/papers/{id}/outline` | 生成大纲 |
| POST | `/api/papers/{id}/generate` | 一键生成（同步） |
| POST | `/api/papers/{id}/stream-generate` | 一键生成（SSE 流式） |
| GET | `/api/papers/{id}/export?format=docx\|pdf\|md` | 导出论文（Word / PDF / Markdown） |
| GET/POST | `/api/chapters/`、`/api/chapters/paper/{paper_id}` | 章节列表 / 创建 |
| POST | `/api/chapters/{id}/generate`、`/api/chapters/{id}/polish` | 撰写 / 润色章节 |
| GET/POST | `/api/references/` | 文献列表 / 新增 |
| POST | `/api/references/search` | RAG 语义检索 |
| POST | `/api/references/rebuild` | 重建向量库 |
| GET | `/api/references/status` | 向量库状态 |
| GET/POST | `/api/papers/{id}/versions` | 版本列表 / 手动保存版本 |
| GET | `/api/papers/{id}/versions/{version_id}` | 版本详情（含全量快照） |
| POST | `/api/papers/{id}/versions/{version_id}/rollback` | 回滚到指定版本 |
| GET | `/api/papers/{id}/versions/{version_id}/diff` | 结构维度差异对比（`?target_version_id=` 可选） |

## 版本管理

论文级**全量快照**版本管理，工作台右上角「🕒 版本管理」进入。

- **快照内容**：Paper + Chapters + References + Outline + 工作流状态，序列化为一份 JSON 快照（全量快照比 diff 更简单可靠）
- **历史版本不可变**：只新增、不修改、不删除（接口层面也没有更新/删除历史版本的入口）
- **自动版本（关键节点）**：

  | 触发节点 | 说明 |
  | --- | --- |
  | `topic` | 选题确认后（修改论文选题时） |
  | `outline` | 大纲生成后 |
  | `references` | 文献引用完成 |
  | `section` | 每章撰写完成（流式生成时逐章增量落库） |
  | `polish` | 润色完成 |
  | `quality_check` | 质量检查通过（复用规则化质检，不额外消耗模型调用） |

- **回滚即新版本**：回滚到 v3 时会先生成「回滚前备份」（当前内容），再恢复 v3 内容，最后生成类型为 `rollback` 的新版本 —— v4、v5 等历史版本全部保留，可随时再回滚回去
- **结构化差异对比**：按 论文标题 / 摘要 / 关键词 / 大纲 / 章节 / 参考文献 六个维度对比，返回逐项状态（新增 / 删除 / 修改 / 未变化）与行内差异片段，前端高亮显示

版本类型：`manual`（手动保存）、`auto`（关键节点自动）、`rollback`（回滚生成）、`backup`（回滚前备份）。

## 说明

- 未配置 API Key 时后端仍可启动，仅 AI 相关接口会返回明确的配置提示（`/health` 中 `llm` 字段为 `not_configured`）。
- SSE 流式接口通过 `?token=` 传递 JWT（`EventSource` 无法自定义请求头），前端使用 `fetch` + 手动解析流。
- 文献为全局库（`paper_id` 可为空），生成论文时自动与当前论文关联。

## 论文导出

工作台「📥 导出」支持三种格式：

| 格式 | 生成方式 | 排版 |
| --- | --- | --- |
| Word（.docx） | 后端 python-docx | 标题黑体居中、正文宋体 12pt、1.5 倍行距、首行缩进 2 字符、列表缩进 |
| PDF | 后端 reportlab（内置 CJK 字体 STSong-Light，无需额外字体文件） | A4、2.5cm 页边距、标题分级、首行缩进 |
| Markdown | 前端直接下载原始 Markdown | — |

导出前会统一清理模型附加的非正文内容（「说明」「注」引用块、「如需扩展为…」「我可随时为您…」等后续服务建议），相关逻辑见 `backend/app/utils/helpers.py` 的 `strip_ai_meta()`，并在 Agent 提示词中同步约束模型只输出正文。
>>>>>>> 5bf49b0f (first commit)
