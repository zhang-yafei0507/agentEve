#!/bin/bash

echo "🚀 Agent Eve - Agentic RAG 多智能体协作系统"
echo "=========================================="
echo ""

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误：需要 Python 3"
    exit 1
fi

echo "✅ Python 版本：$(python3 --version)"

# 安装后端依赖
echo ""
echo "📦 安装后端依赖..."
cd server
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 复制环境配置
if [ ! -f .env ]; then
    echo ""
    echo "⚙️  创建环境配置文件..."
    cp .env.example .env
    echo "请编辑 .env 文件配置 API Key 等参数"
fi

# 初始化数据库
echo ""
echo "🗄️  初始化数据库..."
python -c "from server.utils.db_init import init_db; import asyncio; asyncio.run(init_db())"

# 初始化内置工具
echo ""
echo "🛠️  初始化内置工具..."
python -c "
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from server.database import Tool

async def init():
    engine = create_async_engine('sqlite+aiosqlite:///./agent_eve.db')
    async with engine.begin() as conn:
        builtin_tools = [
            {'name': '联网搜索', 'description': '使用搜索引擎检索互联网信息', 'category': '网络检索', 'icon': '🔍'},
            {'name': '新闻检索', 'description': '检索最新新闻资讯', 'category': '网络检索', 'icon': '📰'},
            {'name': '数据分析', 'description': '进行数据对比、趋势分析等', 'category': '数据分析', 'icon': '📊'},
            {'name': '计算器', 'description': '执行数学计算', 'category': '数据分析', 'icon': '🧮'},
            {'name': '代码解释器', 'description': '执行 Python 代码', 'category': '编程', 'icon': '💻'},
            {'name': '文本摘要', 'description': '提取文本关键信息', 'category': '文本处理', 'icon': '✍️'},
        ]
        for tool_data in builtin_tools:
            tool = Tool(**tool_data)
            conn.add(tool)
        await conn.commit()

asyncio.run(init())
"

echo ""
echo "✅ 后端准备完成！"
echo ""

# 安装前端依赖
echo "📦 安装前端依赖..."
cd ../frontend
npm install

echo ""
echo "✅ 前端准备完成！"
echo ""
echo "=========================================="
echo "🎉 安装完成！"
echo ""
echo "启动服务："
echo "  后端：cd server && source venv/bin/activate && uvicorn server.main:app --reload"
echo "  前端：cd frontend && npm run dev"
echo ""
echo "访问地址：http://localhost:3000"
echo "API 文档：http://localhost:8000/docs"
echo "=========================================="
