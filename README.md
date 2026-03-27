# 🚀 Agent Eve - Agentic RAG 多智能体协作系统

## 📖 项目简介

Agent Eve 是一款**零门槛的智能体协作平台**，用户只需输入问题，系统自动规划任务、创建子智能体、调用工具、协同工作，最终交付高质量答案。

### 核心特性

- ✅ **自动化任务编排**：主智能体自动拆解复杂任务，创建并管理最多 4 个子智能体并行工作
- ✅ **透明化协作过程**：实时查看智能体之间的分工、协作、决策过程
- ✅ **工具即插即用**：通过 MCP 协议无缝集成各类工具
- ✅ **结果可溯源**：每个结论都有明确的来源和推理过程

---

## 🏗️ 技术架构

### 后端技术栈
- **框架**: FastAPI (Python)
- **数据库**: SQLite (MVP) / PostgreSQL (生产)
- **ORM**: SQLAlchemy (异步)
- **协议**: MCP (Model Context Protocol)
- **流式响应**: SSE (Server-Sent Events)

### 前端技术栈
- **框架**: React 18 + Vite
- **状态管理**: Zustand
- **样式**: Tailwind CSS
- **HTTP 客户端**: Axios
- **Markdown 渲染**: Marked

---

## 🚀 快速开始

### 方式一：一键安装脚本（推荐）

```bash
chmod +x setup.sh
./setup.sh
```

### 方式二：手动安装

#### 1. 后端设置

```bash
cd server

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入你的 API Key

# 初始化数据库
python -c "from server.utils.db_init import init_db; import asyncio; asyncio.run(init_db())"

# 启动后端服务
uvicorn server.main:app --reload --host 0.0.0.0 --port 8000
```

#### 2. 前端设置

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

---

## 📁 项目结构

```
agentEve3/
├── server/                      # 后端服务
│   ├── agents/                  # 智能体系统
│   │   └── supervisor.py       # 主智能体与子智能体
│   ├── routes/                  # API 路由
│   │   ├── chat.py             # 聊天接口
│   │   ├── tools.py            # 工具管理
│   │   ├── sessions.py         # 会话管理
│   │   └── mcp.py              # MCP 集成
│   ├── utils/                   # 工具类
│   │   ├── config.py           # 配置管理
│   │   ├── database.py         # 数据库模型
│   │   └── db_init.py          # 数据库初始化
│   ├── main.py                  # 应用入口
│   └── requirements.txt         # Python 依赖
├── frontend/                    # 前端应用
│   ├── src/
│   │   ├── components/          # React 组件
│   │   │   ├── Sidebar.jsx     # 侧边栏
│   │   │   ├── ChatArea.jsx    # 聊天区域
│   │   │   ├── MessageBubble.jsx # 消息气泡
│   │   │   ├── InputArea.jsx   # 输入区域
│   │   │   └── AgentPanel.jsx  # 智能体面板
│   │   ├── store/               # 状态管理
│   │   │   └── index.js        # Zustand store
│   │   ├── services/            # API 服务
│   │   │   └── api.js          # API 封装
│   │   ├── App.jsx              # 根组件
│   │   └── main.jsx             # 入口文件
│   ├── package.json
│   └── vite.config.js
├── setup.sh                     # 安装脚本
└── 需求表.txt                   # 产品需求文档
```

---

## 🎯 核心功能

### 1. 智能体任务编排

**主智能体 (Supervisor)** 职责：
- 意图理解：分析用户查询复杂度
- 任务拆解：将复杂任务分解为 2-4 个子任务
- 智能体分配：根据任务类型创建对应角色的子智能体
- 协作协调：监控进度、处理依赖、解决冲突
- 结果汇总：收集输出、验证一致性、生成最终答案

**子智能体角色**：
- 🔹 **Researcher**: 信息检索、事实查证
- 💻 **Coder**: 代码编写、调试、解释
- 📊 **Analyzer**: 数据分析、对比、趋势预测
- ✍️ **Writer**: 文案创作、报告撰写、总结
- ✅ **Reviewer**: 质量检查、逻辑验证、纠错

### 2. 共享状态板 (Shared Board)

所有智能体共享的信息空间：
- **关键发现** (Key Findings): 从各来源提取的重要数据
- **中间结论** (Intermediate Conclusions): 子智能体的分析结果
- **待解决问题** (Open Questions): 需要其他智能体协助的问题
- **求助请求** (Help Requests): 智能体间的协作请求

### 3. MCP 工具集成

支持三类连接方式：
- **stdio**: 本地进程启动（如 `npx -y mcp-server-fetch`）
- **SSE**: 远程服务器 Server-Sent Events
- **WebSocket**: 实时双向通信

内置工具示例：
- 🔍 联网搜索、📰 新闻检索、🎓 学术搜索
- 📊 图表生成、🧮 计算器、📉 趋势预测
- 💻 代码解释器、✍️ 文本摘要

### 4. 流式响应系统

通过 SSE 实时推送：
- `agent_update`: 智能体状态更新
- `tool_call_start`: 工具调用开始
- `tool_call_result`: 工具调用结果
- `shared_board_update`: 共享状态板更新
- `sub_agent_completed`: 子智能体完成
- `final_answer_chunk`: 最终答案流式输出
- `citation`: 引用信息
- `done`: 完成

---

## 🎨 界面设计

### 左侧侧边栏 (240px)
- Logo + 产品名称
- 新对话按钮（快捷键 Ctrl/Cmd+N）
- 功能菜单：AI 创作、云盘、更多
- 历史对话列表（按时间分组）
- 用户头像（底部）

### 中间主区域
- **空状态**: 欢迎语 + 快捷提问卡片（3 列网格）
- **对话区域**: 
  - 用户消息气泡（右侧，蓝色）
  - AI 消息气泡（左侧，白色）
    - 思考过程折叠面板
    - 子智能体结果卡片
    - 引用来源标注
- **底部输入区**:
  - 工具快捷栏（横向滚动）
  - 主输入框（圆角，自动高度）
  - 功能栏：快速/图像/深入/写作/PPT/视频/语音

### 右侧智能体协作面板 (320px, 可折叠)
- 任务概览（主智能体、子智能体数量、工具调用次数）
- 执行流程图（节点 + 连线动画）
- 共享状态板实时更新
- 智能体日志滚动

---

## 📊 API 端点

### 聊天相关
```
POST   /api/chat/send          # 发送消息（SSE 流式）
GET    /api/chat/history/{id}   # 获取会话历史
```

### 会话管理
```
GET    /api/sessions/list       # 获取会话列表
GET    /api/sessions/{id}       # 获取会话详情
POST   /api/sessions/create     # 创建会话
PUT    /api/sessions/{id}/rename # 重命名会话
DELETE /api/sessions/{id}       # 删除会话
GET    /api/sessions/{id}/export # 导出会话
```

### 工具管理
```
GET    /api/tools/list          # 获取工具列表
GET    /api/tools/{id}          # 获取工具详情
PUT    /api/tools/{id}/toggle   # 启用/禁用工具
PUT    /api/tools/{id}/config   # 更新工具配置
POST   /api/tools/builtin/init  # 初始化内置工具
```

### MCP 集成
```
GET    /api/mcp/servers/list    # 获取 MCP 服务器列表
POST   /api/mcp/servers/add     # 添加 MCP 服务器
DELETE /api/mcp/servers/{id}    # 删除 MCP 服务器
POST   /api/mcp/servers/{id}/test # 测试连接
GET    /api/mcp/tools/discover  # 获取 MCP 工具
```

---

## 🧪 测试用例

### 场景 1：复杂财报分析
```
用户输入：帮我分析特斯拉 2025 年 Q1 财报，对比比亚迪，给出投资建议

预期流程：
1. 主智能体创建 4 个子智能体：Researcher、Analyzer、RiskAgent、Writer
2. Researcher 检索财报数据 → 写入共享状态板
3. Analyzer 读取状态板 → 对比分析 → 写入结论
4. RiskAgent 分析风险因素
5. Writer 整合所有信息 → 生成报告
6. 主智能体汇总 → 返回最终答案

验收标准：
✅ 4 个子智能体全部创建并执行
✅ 共享状态板至少有 5 条关键信息
✅ 最终答案包含数据对比、风险分析、投资建议
✅ 总耗时 < 30s
```

### 场景 2：工具调用失败
```
用户输入：查询苹果公司最新股价
模拟股票工具故障

预期流程：
1. 调用股票工具 → 超时/500 错误
2. 自动重试（最多 3 次）
3. 重试失败 → 降级方案
4. 提示用户并提供替代方案

验收标准：
✅ 显示清晰的错误提示
✅ 提供可行的替代方案
✅ 用户无需重新输入问题
```

---

## 🔧 配置说明

### 环境变量 (.env)

```bash
# 服务器配置
HOST=0.0.0.0
PORT=8000
DEBUG=True

# 数据库
DATABASE_URL=sqlite+aiosqlite:///./agent_eve.db

# LLM 配置
LLM_PROVIDER=openai
LLM_API_KEY=your-api-key-here
LLM_MODEL=gpt-4-turbo-preview

# MCP 设置
MCP_TIMEOUT=30
MAX_SUB_AGENTS=4

# CORS
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173
```

---

## 🛣️ 开发路线图

### Phase 1 (MVP, 2 周) ✅
- [x] 基础聊天界面
- [x] 主智能体（简单任务直接回答）
- [x] 1-2 个内置工具
- [x] 流式响应（SSE）
- [x] 会话保存

### Phase 2 (核心功能，3 周) 🚧
- [x] 子智能体创建与编排（最多 4 个）
- [x] 共享状态板（基础读写）
- [x] MCP 工具集成（stdio 连接）
- [x] 智能体协作可视化（流程图）
- [x] 工具管理页面

### Phase 3 (增强体验，2 周) ⏳
- [ ] 子智能体结果卡片（可展开）
- [ ] 引用标注与溯源
- [ ] 错误处理与降级方案
- [ ] 响应式设计（移动端适配）
- [ ] 性能优化

### Phase 4 (高级功能，3 周) 📅
- [ ] 子智能体主动协作（求助 - 响应）
- [ ] 多轮对话上下文管理
- [ ] 会话导出/分享
- [ ] 高级可视化工具（React Flow）
- [ ] 监控与日志系统

---

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

### 开发环境设置
1. Fork 本项目
2. 克隆到本地
3. 按照"快速开始"安装依赖
4. 创建功能分支：`git checkout -b feature/your-feature`
5. 提交更改：`git commit -m 'Add some feature'`
6. 推送到分支：`git push origin feature/your-feature`
7. 提交 Pull Request

---

## 📄 许可证

MIT License

---

## 📞 联系方式

- 项目地址：https://github.com/yourusername/agent-eve
- 问题反馈：请提交 Issue
- 合作联系：your-email@example.com

---

**🎉 开始使用 Agent Eve，体验智能体协作的强大能力！**
