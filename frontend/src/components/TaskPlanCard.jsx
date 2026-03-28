import React, { useState } from 'react';

/**
 * 任务规划卡片
 * 展示多步骤任务的执行进度
 */
const TaskPlanCard = ({ taskPlan, completedSteps = 0 }) => {
  const [isExpanded, setIsExpanded] = useState(true);

  if (!taskPlan || !taskPlan.steps) return null;

  const totalSteps = taskPlan.total_steps || taskPlan.steps.length;
  const progress = totalSteps > 0 ? Math.round((completedSteps / totalSteps) * 100) : 0;
  
  // 关键修复：支持逐步揭示步骤
  const revealedSteps = taskPlan.steps.filter(step => step.revealed !== false || step.status === 'completed');

  return (
    <div className="mb-4 bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-lg overflow-hidden">
      {/* 标题栏 - 可点击折叠/展开 */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-4 py-3 bg-white border-b border-blue-100 flex items-center justify-between hover:bg-blue-50 transition-colors"
      >
        <div className="flex items-center gap-3">
          <span className="text-lg">📋</span>
          <div>
            <span className="font-semibold text-blue-800">任务规划</span>
            <span className="ml-2 text-xs text-blue-600 bg-blue-100 px-2 py-1 rounded-full">
              {totalSteps} 步
            </span>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {/* 进度条 */}
          <div className="w-32 h-2 bg-gray-200 rounded-full overflow-hidden">
            <div 
              className="h-full bg-gradient-to-r from-blue-500 to-indigo-500 transition-all duration-500"
              style={{ width: `${progress}%` }}
            />
          </div>
          <span className={`text-blue-400 transform transition-transform ${isExpanded ? 'rotate-180' : ''}`}>
            ▼
          </span>
        </div>
      </button>

      {/* 步骤列表 */}
      {isExpanded && (
        <div className="p-4 space-y-3">
          {taskPlan.steps.map((step, index) => {
            // 关键修复：只有已揭示的步骤才显示
            if (step.revealed === false && step.status !== 'completed') {
              return null;
            }
            
            const isCompleted = index < completedSteps || step.status === 'completed';
            const isCurrent = index === completedSteps || step.status === 'running';
            
            return (
              <div
                key={index}
                className={`flex items-start gap-3 p-3 rounded-lg border-l-4 transition-all ${
                  isCompleted
                    ? 'bg-green-50 border-green-500'
                    : isCurrent
                    ? 'bg-blue-50 border-blue-500 animate-pulse'
                    : 'bg-gray-50 border-gray-300'
                }`}
              >
                {/* 步骤状态图标 */}
                <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center font-bold text-sm ${
                  isCompleted
                    ? 'bg-green-500 text-white'
                    : isCurrent
                    ? 'bg-blue-500 text-white animate-pulse'
                    : 'bg-gray-300 text-gray-600'
                }`}>
                  {isCompleted ? '✓' : step.step}
                </div>
                
                {/* 步骤内容 */}
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-medium text-gray-800">
                      {getRoleIcon(step.role)} {step.role}
                    </span>
                    {isCurrent && (
                      <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded animate-pulse">
                        执行中...
                      </span>
                    )}
                    {isCompleted && (
                      <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded">
                        完成
                      </span>
                    )}
                  </div>
                  <div className="text-sm text-gray-600">{step.task}</div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

// 辅助函数：获取角色图标
function getRoleIcon(role) {
  const icons = {
    researcher: '🔹',
    coder: '💻',
    analyzer: '📊',
    writer: '✍️',
    reviewer: '✅'
  };
  return icons[role?.toLowerCase()] || '🔹';
}

export default TaskPlanCard;
