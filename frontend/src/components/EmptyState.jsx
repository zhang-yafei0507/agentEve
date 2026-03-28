import React, { useEffect, useState } from 'react';
import api from '../services/api';

const EmptyState = ({ onQuickAsk }) => {
  const [quickQuestions, setQuickQuestions] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // 从后端获取快捷问题
    const fetchQuestions = async () => {
      try {
        const data = await api.getQuickQuestions();
        setQuickQuestions(data.questions || []);
      } catch (error) {
        console.error('加载快捷问题失败:', error);
        // 降级方案：使用默认问题
        setQuickQuestions(DEFAULT_QUESTIONS);
      } finally {
        setLoading(false);
      }
    };

    fetchQuestions();
  }, []);

  const categories = [
    { id: 'research', label: '资讯调研', icon: '🔍' },
    { id: 'analysis', label: '数据分析', icon: '📊' },
    { id: 'coding', label: '编程开发', icon: '💻' },
    { id: 'writing', label: '文案创作', icon: '✍️' }
  ];

  const getCategoryIcon = (categoryId) => {
    const category = categories.find(c => c.id === categoryId);
    return category?.icon || '❓';
  };

  const getCategoryLabel = (categoryId) => {
    const category = categories.find(c => c.id === categoryId);
    return category?.label || categoryId;
  };

  return (
    <div className="flex-1 flex flex-col items-center justify-center p-8 bg-gradient-to-br from-gray-50 to-blue-50">
      {/* 欢迎标题 */}
      <div className="text-center mb-12">
        <h1 className="text-5xl font-bold text-gray-800 mb-4">
          🤖 有什么我能帮你的吗？
        </h1>
        <p className="text-xl text-gray-600">
          智能体协作系统，帮你处理复杂任务
        </p>
      </div>

      {/* 功能特性 */}
      <div className="grid grid-cols-3 gap-6 max-w-5xl mb-12">
        <FeatureCard
          icon="🧠"
          title="多智能体协作"
          description="Researcher、Analyzer、Coder 等多个智能体并行工作"
        />
        <FeatureCard
          icon="🛠️"
          title="强大工具集成"
          description="支持 MCP 协议，可调用各种外部工具和服务"
        />
        <FeatureCard
          icon="📊"
          title="实时可视化"
          description="透明化展示智能体协作流程和思考过程"
        />
      </div>

      {/* 快捷提问 */}
      <div className="w-full max-w-5xl">
        <h2 className="text-2xl font-bold text-gray-800 mb-6 text-center">
          💡 试试这些提问
        </h2>

        {loading ? (
          <div className="col-span-3 text-center text-gray-500 py-8">
            加载中...
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {quickQuestions.map((question, index) => (
              <button
                key={index}
                onClick={() => onQuickAsk(question.text)}
                className="p-5 bg-white hover:bg-blue-50 rounded-xl text-left transition-all cursor-pointer border-2 border-transparent hover:border-blue-200 shadow-sm hover:shadow-md"
              >
                <div className="flex items-start gap-3">
                  <span className="text-2xl">{getCategoryIcon(question.category)}</span>
                  <div className="flex-1">
                    <div className="text-sm line-clamp-2 text-gray-700 font-medium mb-2">
                      {question.text}
                    </div>
                    <div className="text-xs text-gray-400">
                      {getCategoryLabel(question.category)}
                    </div>
                  </div>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* 底部提示 */}
      <div className="mt-12 text-center text-gray-500 text-sm">
        <p>💡 提示：点击任意问题快速开始，或在下方输入框输入你的问题</p>
      </div>
    </div>
  );
};

// 功能特性卡片
const FeatureCard = ({ icon, title, description }) => (
  <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100 text-center hover:shadow-md transition-shadow">
    <div className="text-4xl mb-3">{icon}</div>
    <h3 className="font-bold text-gray-800 mb-2">{title}</h3>
    <p className="text-sm text-gray-600">{description}</p>
  </div>
);

// 默认快捷问题（降级方案）
const DEFAULT_QUESTIONS = [
  { text: "帮我分析一下特斯拉 2025 年 Q1 财报", category: "analysis" },
  { text: "最近 AI 领域有什么重要新闻？", category: "research" },
  { text: "用 Python 写一个快速排序算法", category: "coding" },
  { text: "对比比亚迪和蔚来汽车的商业模式", category: "analysis" },
  { text: "帮我写一篇关于气候变化的科普文章", category: "writing" },
  { text: "查询英伟达最新股价和市值", category: "research" },
  { text: "解释什么是 Transformer 架构", category: "analysis" },
  { text: "创建一个简单的待办事项管理网页", category: "coding" },
  { text: "总结《人类简史》这本书的核心观点", category: "writing" }
];

export default EmptyState;
