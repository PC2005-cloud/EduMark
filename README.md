# EduMark — 基于大模型的中小学作业批改系统

自动识别和批改中小学生作业的智能批改系统，利用阿里云 OCR、百炼视觉模型和大语言模型，实现从作业图像上传到自动批改的全流程。

---

## 功能

### 作业批改
- 上传作业图片（支持多张），系统自动识别题目和学生答案
- 双引擎可选：**阿里云 OCR**（传统切题+文字识别）或 **百炼视觉模型**（端到端图像理解）
- **图像预处理**：对比度+锐度增强，可选开关
- **大模型批改**：调用百炼 Qwen-Plus 对学生答案评分，输出得分/评语/解题分析
- **知识库检索增强（RAG）**：批改时自动检索向量知识库中的相关知识片段，提升评分准确性
- 支持跨页题目合并（百炼模式多图输入）
- 全异步处理：Celery 后台执行，前端轮询结果

### 知识库管理
- 上传知识文档（PDF / PPT / Word），系统自动解析
- 文档经 MinerU 解析 → 文本分块 → 向量化 → 存入 Qdrant 向量库
- 图片自动转为文字描述（百炼视觉模型）
- 批改时自动检索相关知识块作为评分参考

### 用户管理
- 三种角色：管理员（Admin）/ 教师（Teacher）/ 学生（Student）
- JWT 双 Token 认证（Access + Refresh）
- 用户个性化配置（识别模式/模型选择/功能开关）

---

## 快速开始

### 环境要求
- Python 3.12+
- UV 包管理器
- MySQL 8.0+、Redis、MinIO、Qdrant

### 安装依赖

```bash
uv sync
```

### 启动 API 服务

```bash
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 启动 Celery Worker

```bash
uv run celery -A app.tasks.celery_app worker --loglevel=info -P solo
```

### 接口文档

启动后访问：

| 地址 | 说明 |
|---|---|
| `http://localhost:8000/docs` | Swagger UI |
| `http://localhost:8000/redoc` | ReDoc |
| `http://localhost:8000/openapi.json` | OpenAPI JSON 下载 |

---

## 核心流程

### 作业批改流程

```
POST /homework/submit → 返回 task_id
  → Celery 异步执行：
    下载图片 → 预处理（可选）→ OCR 识别 → 保存题目
    → 检索知识库（可选）→ LLM 批改 → 保存得分/评语

前端轮询 GET /homework/status/{task_id}
完成后 GET /homework/result/{task_id} 获取完整结果
```

### 知识文档流程

```
POST /knowledge/upload → 返回 knowledge_id
  → Celery 异步执行：
    存 MinIO → MinerU 解析 → 文本分块 → Embedding → 写入 Qdrant

前端轮询 GET /knowledge/{id} 查看解析状态
```

---

## 技术栈

| 层面 | 选型 |
|---|---|
| 后端 | FastAPI + SQLAlchemy |
| 数据库 | MySQL 8.0 |
| 任务队列 | Celery + Redis |
| 对象存储 | MinIO |
| 向量数据库 | Qdrant |
| 图像预处理 | Pillow |
| 识别引擎一 | 阿里云 OCR |
| 识别引擎二 | 百炼 Qwen-VL |
| 批改引擎 | 百炼 Qwen-Plus |
| 向量化模型 | text-embedding-v4 |
| 文档解析 | MinerU |

---

## 接口概览

| 方法 | 路径 | 说明 | 权限 |
|---|---|---|---|
| POST | `/auth/register` | 用户注册 | 公开 |
| POST | `/auth/login` | 登录 | 公开 |
| POST | `/auth/refresh` | 刷新令牌 | 公开 |
| GET | `/auth/me` | 当前用户 | 登录 |
| GET | `/users/{id}` | 用户详情 | 管理员 |
| POST | `/users` | 新增用户 | 管理员 |
| PUT | `/users/{id}` | 编辑用户 | 管理员 |
| DELETE | `/users/{id}` | 删除用户 | 管理员 |
| POST | `/users/page` | 用户列表 | 管理员 |
| GET | `/config/me` | 查看配置 | 登录 |
| PUT | `/config/me` | 修改配置 | 登录 |
| POST | `/homework/submit` | 提交作业 | 登录 |
| GET | `/homework/status/{tid}` | 批改进度 | 登录 |
| GET | `/homework/result/{tid}` | 批改结果 | 登录 |
| POST | `/homework/task/page` | 任务列表 | 登录 |
| GET | `/knowledge/{id}` | 文档详情 | 登录 |
| DELETE | `/knowledge/{id}` | 删除文档 | 教师/管理员 |
| POST | `/knowledge/page` | 文档列表 | 登录 |
| POST | `/knowledge/upload` | 上传文档 | 教师/管理员 |
| GET | `/models/{id}` | 模型详情 | 登录 |
| POST | `/models` | 新增模型 | 管理员 |
| PUT | `/models/{id}` | 编辑模型 | 管理员 |
| DELETE | `/models/{id}` | 删除模型 | 管理员 |
| POST | `/models/page` | 模型列表 | 登录 |

---

## 数据库

10 张关系表：`user` → `task` → `image` / `question` → `block` → `correction`，`knowledge` → `question_chunk`，`config`，`model`

向量库：Qdrant `knowledge_chunks`（1536 维，Cosine 距离）

---

## Docker 部署

### 检查环境
- 检查wsl环境

```
wsl -l -v
```

```
 NAME              STATE           VERSION
* Ubuntu-22.04      Running         2
  docker-desktop    Running         2
```

- 确保已安装 Docker Desktop

```
docker --version
docker-compose --version
docker ps
```

### 构建镜像

```bash
docker build -t edumark-fastapi:latest .
```

### 生成配置文件

双击 `init-deploy.bat` 生成配置文件（MySQL / Redis / MinIO / Qdrant / Nginx 配置），然后复制到 Linux 服务器。

### 启动服务

```bash
docker-compose -f /EduMark/em-com.yml up -d
```
