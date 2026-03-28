import React, { useState } from 'react';

/**
 * 主智能体思考过程卡片
 * 展示主智能体的实时思考内容
 */
const SupervisorThoughtCard = ({ thoughts }) => {
  const [isExpanded, setIsExpanded] = useState(true);

  if (!thoughts || thoughts.length === 0) return null;

  return (
    <div className="mb-4 bg-gradient-to-r from-purple-50 to-blue-50 border border-purple-200 rounded-lg overflow-hidden">
      {/* 标题栏 - 可点击折叠/展开 */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-4 py-3 bg-white border-b border-purple-100 flex items-center justify-between hover:bg-purple-50 transition-colors"
      >
        <div className="flex items-center gap-2">
          <span className="text-lg">🧠</span>
          <span className="font-semibold text-purple-800">主智能体思考过程</span>
          <span className="text-xs text-purple-600 bg-purple-100 px-2 py-1 rounded-full">
            {thoughts.length} 条
          </span>
        </div>
        <span className={`text-purple-400 transform transition-transform ${isExpanded ? 'rotate-180' : ''}`}>
          ▼
        </span>
      </button>

      {/* 思考内容列表 */}
      {isExpanded && (
        <div className="p-4 space-y-2 max-h-96 overflow-y-auto">
          {thoughts.map((thought, index) => (
            <div
              key={index}
              className={`flex items-start gap-3 p-3 rounded-lg transition-all ${
                thought.type === 'decision'
                  ? 'bg-blue-100 border-l-4 border-blue-500'
                  : 'bg-white border-l-4 border-purple-400'
              }`}
            >
              {/* 步骤指示器 */}
              {thought.step && (
                <div className="flex-shrink-0 w-6 h-6 rounded-full bg-purple-500 text-white flex items-center justify-center text-xs font-bold">
                  {thought.step}
                </div>
              )}
              
              {/* 思考内容 */}
              <div className="flex-1">
                {thought.type === 'decision' ? (
                  <>
                    <div className="font-medium text-blue-800 mb-1">
                      📌 决策：{thought.decision === 'complex_task' ? '复杂任务' : '简单任务'}
                    </div>
                    <div className="text-sm text-blue-700">{thought.message}</div>
                    {thought.reasoning && (
                      <div className="mt-2 text-xs text-blue-600 bg-blue-50 p-2 rounded">
                        💡 {thought.reasoning}
                      </div>
                    )}
                  </>
                ) : (
                  <>
                    <div className="text-sm text-gray-600">
                      {thought.action === 'analyzing_query' && '🔍'}
                      {thought.action === 'starting_step' && '▶️'}
                      {thought.action === 'step_completed' && '✅'}
                      {thought.action === 'aggregating' && '🔄'}
                      {' '}{thought.message}
                    </div>
                    {thought.timestamp && (
                      <div className="text-xs text-gray-400 mt-1">
                        {new Date(thought.timestamp).toLocaleTimeString()}
                      </div>
                    )}
                  </>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default SupervisorThoughtCard;
