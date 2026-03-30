/**
 * 反思历史时间线组件
 * 展示 ReAct 循环中的反思过程和策略调整
 */
import React, { useState } from 'react';

const ReflectionTimeline = ({ reflections }) => {
  const [isExpanded, setIsExpanded] = useState(true);
  
  if (!reflections || reflections.length === 0) {
    return null;
  }
  
  // 计算平均质量分数
  const avgQuality = reflections.reduce((sum, r) => sum + (r.quality_score || 0), 0) / reflections.length;
  
  return (
    <div className="mb-4 border border-purple-200 rounded-lg overflow-hidden">
      {/* 头部 - 可折叠 */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-4 py-3 bg-purple-50 flex items-center justify-between hover:bg-purple-100 transition-colors"
      >
        <div className="flex items-center gap-2">
          <span className="text-xl">🤔</span>
          <div className="text-left">
            <h3 className="font-medium text-gray-800">反思历史</h3>
            <p className="text-xs text-gray-500">
              {reflections.length} 次反思 · 平均质量：{(avgQuality * 100).toFixed(0)}%
            </p>
          </div>
        </div>
        <span className="text-gray-400 text-sm">
          {isExpanded ? '▲' : '▼'}
        </span>
      </button>
      
      {/* 展开内容 */}
      {isExpanded && (
        <div className="px-4 py-3 bg-white space-y-3 max-h-96 overflow-y-auto">
          {reflections.map((reflection, index) => (
            <div
              key={index}
              className={`border-l-4 pl-3 py-2 ${
                reflection.should_finish 
                  ? 'border-green-500 bg-green-50' 
                  : 'border-purple-500 bg-purple-50'
              }`}
            >
              {/* 步骤信息 */}
              <div className="flex items-center gap-2 mb-2">
                <span className="text-xs font-medium text-gray-600">
                  步骤 {reflection.step || index + 1}
                </span>
                <span className={`text-xs px-2 py-0.5 rounded-full ${
                  reflection.quality_score >= 0.8 
                    ? 'bg-green-100 text-green-700' 
                    : reflection.quality_score >= 0.5
                    ? 'bg-yellow-100 text-yellow-700'
                    : 'bg-red-100 text-red-700'
                }`}>
                  质量：{(reflection.quality_score * 100).toFixed(0)}%
                </span>
              </div>
              
              {/* 观察摘要 */}
              <p className="text-sm text-gray-700 mb-2">
                <span className="font-medium">观察：</span>
                {reflection.observation_summary || '无观察结果'}
              </p>
              
              {/* 策略调整 */}
              {reflection.adjustment && (
                <p className="text-sm text-gray-700 mb-2">
                  <span className="font-medium">调整：</span>
                  {reflection.adjustment}
                </p>
              )}
              
              {/* 决策 */}
              <div className="flex items-center gap-2 text-xs">
                <span className="text-gray-600">决策：</span>
                {reflection.should_finish ? (
                  <span className="text-green-600 font-medium">✅ 完成任务</span>
                ) : reflection.should_continue ? (
                  <span className="text-blue-600 font-medium">➡️ 继续执行</span>
                ) : (
                  <span className="text-red-600 font-medium">❌ 停止执行</span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default ReflectionTimeline;
