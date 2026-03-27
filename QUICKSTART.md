# Agent Eve 快速启动指南

## 🚀 一键启动

### 1. 首次安装
```bash
chmod +x setup.sh
./setup.sh
```

### 2. 配置 API Key
编辑 `server/.env` 文件：
```bash
LLM_API_KEY=your-openai-api-key-here
```

### 3. 启动后端
```bash
cd server
source venv/bin/activate
uvicorn server.main:app --reload --host 0.0.0.0 --port 8000
```

### 4. 启动前端
```bash
cd frontend
npm run dev
```

### 5. 访问应用
- 前端地址：http://localhost:3000
- API 文档：http://localhost:8000/docs

---

## 💡 使用示例

### 简单问题
```
今天天气怎么样？
```
→ 主智能体直接回答

### 复杂分析
```
帮我分析特斯拉 2025 年 Q1 财报，对比比亚迪，给出投资建议
```
→ 创建 4 个子智能体：
   - Researcher: 检索财报数据
   - Analyzer: 对比分析指标
   - RiskAgent: 评估风险因素
   - Writer: 生成投资报告

### 编程任务
```
用 Python 写一个爬虫，爬取天气数据并生成图表
```
→ 创建 2 个子智能体：
   - Coder: 编写代码
   - Reviewer: 代码审查

---

## 🔧 常见问题

### Q: 如何添加自定义工具？
A: 在工具管理页面点击"添加 MCP Server"，选择连接方式（stdio/SSE/WebSocket），填写配置即可。

### Q: 智能体数量可以调整吗？
A: 修改 `.env` 中的 `MAX_SUB_AGENTS` 参数（默认 4）。

### Q: 如何查看智能体协作流程？
A: 点击输入框上方的"👁️ 协作流程"按钮，右侧会显示智能体面板。

### Q: 支持移动端吗？
A: 是的，系统采用响应式设计，移动端会自动调整布局。

---

## 📞 技术支持

如有问题，请：
1. 查看 README.md 详细文档
2. 访问 API 文档：http://localhost:8000/docs
3. 提交 Issue

祝使用愉快！🎉
