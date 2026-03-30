import React, { useState } from 'react';

/**
 * 工具调用卡片
 * 展示单个工具调用的参数、执行状态、结果
 */
const ToolCallCard = ({ toolCall }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  if (!toolCall) return null;

  const {
    tool,
    agent_id,
    step,
    status,
    params,
    result,
    duration,
    start_time,
    end_time
  } = toolCall;

  // 状态样式映射
  const statusStyles = {
    running: 'bg-blue-50 border-blue-300 text-blue-700',
    success: 'bg-green-50 border-green-300 text-green-700',
    failed: 'bg-red-50 border-red-300 text-red-700',
    pending: 'bg-gray-50 border-gray-300 text-gray-700'
  };

  const statusLabels = {
    running: '执行中...',
    success: '成功',
    failed: '失败',
    pending: '等待中'
  };

  const statusIcons = {
    running: '⚙️',
    success: '✅',
    failed: '❌',
    pending: '⏳'
  };

  return (
    <div className={`mb-3 border rounded-lg overflow-hidden transition-all ${statusStyles[status] || statusStyles.pending}`}>
      {/* 标题栏 - 可点击展开/折叠 */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-4 py-3 flex items-center justify-between hover:bg-black/5 transition-colors"
      >
        <div className="flex items-center gap-3">
          <span className="text-lg">{statusIcons[status]}</span>
          <div className="text-left">
            <div className="font-medium">
              {tool}
              {step && (
                <span className="ml-2 text-xs opacity-75">
                  (步骤 {step})
                </span>
              )}
            </div>
            <div className="text-xs opacity-75">
              {agent_id ? `智能体：${agent_id.substring(0, 8)}...` : ''}
            </div>
          </div>
        </div>
        
        <div className="flex items-center gap-3">
          {/* 状态标签 */}
          <span className={`text-xs px-2 py-1 rounded-full ${statusStyles[status] || statusStyles.pending}`}>
            {statusLabels[status] || status}
          </span>
          
          {/* 耗时 */}
          {duration && (
            <span className="text-xs opacity-75">
              {duration.toFixed(1)}s
            </span>
          )}
          
          {/* 展开/折叠图标 */}
          <span className={`text-gray-400 transform transition-transform ${isExpanded ? 'rotate-180' : ''}`}>
            ▼
          </span>
        </div>
      </button>

      {/* 详细内容 - 展开时显示 */}
      {isExpanded && (
        <div className="px-4 pb-4 space-y-3 bg-white/50">
          {/* 调用参数 */}
          {params && Object.keys(params).length > 0 && (
            <div>
              <div className="text-xs font-medium mb-1">调用参数：</div>
              <pre className="text-xs bg-gray-100 p-2 rounded overflow-x-auto">
                {JSON.stringify(params, null, 2)}
              </pre>
            </div>
          )}

          {/* 执行结果 */}
          {result && (
            <div>
              <div className="text-xs font-medium mb-1">执行结果：</div>
              <div className="text-xs bg-gray-100 p-2 rounded">
                {typeof result === 'string' ? result : JSON.stringify(result, null, 2)}
              </div>
            </div>
          )}

          {/* 时间信息 */}
          {(start_time || end_time) && (
            <div className="text-xs opacity-75">
              {start_time && <div>开始：{new Date(start_time).toLocaleTimeString()}</div>}
              {end_time && <div>结束：{new Date(end_time).toLocaleTimeString()}</div>}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default ToolCallCard;
