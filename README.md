# FastAPI 应用

一个基于 FastAPI 的应用。

## 项目结构

```
my-app-python/
├── api/                      # API路由
├── config/                   # 配置文件
├── services/                 # 业务服务层
├── venv/                     # 虚拟环境
├── main.py                   # 应用入口
├── requirements.txt          # 依赖
├── .env                      # 环境变量配置
├── .env.example              # 环境变量示例
└── README.md
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env` 并填入你的配置：

```bash
cp .env.example .env
```

编辑 `.env` 文件，配置数据库和邮件服务器信息。

### 3. 运行应用

```bash
uvicorn main:app --reload
```

```bash
python main.py
```

应用将在 `http://localhost:8000` 启动。


