import React from 'react';
import { useStore } from '../store';

const AgentPanel = ({ onClose }) => {
  // 关键修复：使用选择器来获取状态
  const activeAgents = useStore((state) => state.activeAgents);
  const sharedBoard = useStore((state) => state.sharedBoard);
  const currentMessageId = useStore((state) => state.currentMessageId);
  const messages = useStore((state) => state.messages);
  
  // 从 activeAgents 中提取主智能体信息（如果有）
  const supervisorAgent = activeAgents?.find(a => a.agent === 'supervisor');
  const subAgents = activeAgents?.filter(a => a.agent !== 'supervisor') || [];
  
  // 关键修复：如果当前有正在流式的消息，优先显示该消息的智能体状态
  // 否则显示最后一条完成的消息的智能体状态
  const currentStreamingMessage = messages.find(m => m.id === currentMessageId && m.status === 'streaming');
  const lastCompletedMessageWithAgents = messages.filter(
    m => m.role === 'assistant' && m.sub_agent_results && m.sub_agent_results.length > 0
  ).pop();

  return (
    <div className="w-80 bg-white border-l border-gray-200 flex flex-col h-full">
      {/* 标题栏 */}
      <div className="p-4 border-b border-gray-200 flex items-center justify-between">
        <h2 className="font-bold text-lg">🤖 智能体协作流程</h2>
        <button
          onClick={onClose}
          className="text-gray-400 hover:text-gray-600"
        >
          ✕
        </button>
      </div>

      {/* 任务概览 */}
      <div className="p-4 border-b border-gray-200">
        <h3 className="text-sm font-medium text-gray-700 mb-2">📊 任务概览</h3>
        <div className="space-y-1 text-sm text-gray-600">
          <div>• 主智能体：规划师</div>
          <div>• 子智能体：{activeAgents ? activeAgents.length : 0}/4 活跃</div>
          <div>• 工具调用：{activeAgents ? activeAgents.reduce((sum, a) => sum + (a.tool_calls || 0), 0) : 0} 次</div>
        </div>
      </div>

      {/* 执行流程图 */}
      <div className="flex-1 overflow-y-auto p-4">
        <h3 className="text-sm font-medium text-gray-700 mb-3">🔄 执行流程</h3>
        
        {/* 提示当前显示的状态来源 */}
        {currentStreamingMessage && (
          <div className="mb-3 text-xs bg-blue-50 border border-blue-200 rounded p-2 text-blue-700">
            📊 显示实时流式状态 (消息 ID: {currentStreamingMessage.id.substring(0, 8)}...)
          </div>
        )}
        {!currentStreamingMessage && lastCompletedMessageWithAgents && (
          <div className="mb-3 text-xs bg-gray-50 border border-gray-200 rounded p-2 text-gray-600">
            📋 显示最近完成的智能体协作 (消息 ID: {lastCompletedMessageWithAgents.id.substring(0, 8)}...)
          </div>
        )}
        
        <div className="space-y-4">
          {/* 主智能体 */}
          <div className="bg-yellow-50 border-2 border-yellow-400 rounded-lg p-3 relative">
            <div className="font-medium text-yellow-800">🧠 主智能体</div>
            <div className="text-xs text-yellow-600 mt-1">任务规划与协调</div>
            {supervisorAgent && (
              <div className="mt-2 text-xs text-yellow-700">
                <div className="font-medium mb-1">{supervisorAgent.message || '正在规划...'}</div>
                {supervisorAgent.sub_tasks && supervisorAgent.sub_tasks.length > 0 && (
                  <div className="ml-2 space-y-1">
                    {supervisorAgent.sub_tasks.map((task, idx) => (
                      <div key={idx} className="text-xs text-yellow-600">
                        • {task}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
            <div className="absolute -bottom-2 left-1/2 -translate-x-1/2 w-0.5 h-4 bg-yellow-400"></div>
          </div>

          {/* 子智能体 */}
          {subAgents.length > 0 && subAgents.map((agent, index) => (
            <React.Fragment key={agent.agent_id || index}>
              <div className="ml-6 bg-blue-50 border-2 border-blue-400 rounded-lg p-3">
                <div className="flex items-center justify-between">
                  <div className="font-medium text-blue-800">
                    {getAgentIcon(agent.role)} {agent.role}
                  </div>
                  <StatusBadge status={agent.status} />
                </div>
                <div className="text-xs text-blue-600 mt-1">
                  {agent.task || agent.message || '执行中...'}
                </div>
                {agent.tools && agent.tools.length > 0 && (
                  <div className="text-xs text-blue-500 mt-1 flex gap-1 flex-wrap">
                    {agent.tools.map((tool, idx) => (
                      <span key={idx} className="px-1.5 py-0.5 bg-blue-100 rounded text-xs">
                        {tool}
                      </span>
                    ))}
                  </div>
                )}
                {agent.duration && (
                  <div className="text-xs text-gray-500 mt-1">
                    耗时：{agent.duration.toFixed(1)}s
                  </div>
                )}
                {agent.tool_calls !== undefined && (
                  <div className="text-xs text-gray-500 mt-1">
                    工具调用：{agent.tool_calls} 次
                  </div>
                )}
              </div>
              
              {index < subAgents.length - 1 && (
                <div className="ml-9 w-0.5 h-4 bg-blue-300"></div>
              )}
            </React.Fragment>
          ))}
          
          {/* 如果没有子智能体，显示提示 */}
          {(!activeAgents || activeAgents.length === 0) && (
            <div className="ml-6 bg-gray-50 border-2 border-gray-300 rounded-lg p-3">
              <div className="text-sm text-gray-600">等待任务分配...</div>
            </div>
          )}

          {/* 汇总节点 */}
          {subAgents.length > 0 && (
            <>
              <div className="ml-6 bg-green-50 border-2 border-green-400 rounded-lg p-3">
                <div className="font-medium text-green-800">✨ 汇总答案</div>
                {supervisorAgent?.status === 'aggregating' && (
                  <div className="text-xs text-green-600 mt-1">
                    正在汇总 {supervisorAgent.completed_count || 0}/{supervisorAgent.total_count || 0} 个智能体结果...
                  </div>
                )}
              </div>
            </>
          )}
        </div>

        {/* 共享状态板 */}
        <div className="mt-6">
          <h3 className="text-sm font-medium text-gray-700 mb-3">📋 共享状态板</h3>
          
          <div className="space-y-2">
            {sharedBoard.key_findings && sharedBoard.key_findings.length > 0 && (
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
                <h4 className="text-xs font-medium text-blue-800 mb-2">关键发现</h4>
                <div className="space-y-1">
                  {sharedBoard.key_findings.map((finding, index) => (
                    <div key={index} className="text-xs text-gray-700">
                      • {finding.key}: <span className="font-medium">{finding.value}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {sharedBoard.intermediate_conclusions && sharedBoard.intermediate_conclusions.length > 0 && (
              <div className="bg-purple-50 border border-purple-200 rounded-lg p-3">
                <h4 className="text-xs font-medium text-purple-800 mb-2">中间结论</h4>
                <div className="space-y-1">
                  {sharedBoard.intermediate_conclusions.map((conclusion, index) => (
                    <div key={index} className="text-xs text-gray-700">
                      • {conclusion.conclusion}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* 智能体日志 */}
        <div className="mt-6">
          <h3 className="text-sm font-medium text-gray-700 mb-3">📝 智能体日志</h3>
          <div className="space-y-1 text-xs">
            {activeAgents && activeAgents.map((agent, index) => (
              <div key={index} className="flex items-start gap-2 text-gray-600">
                <span className="text-gray-400 flex-shrink-0">
                  [{new Date().toLocaleTimeString()}]
                </span>
                <span>{agent.role}: {agent.message || '执行中...'}</span>
              </div>
            ))}
            {(!activeAgents || activeAgents.length === 0) && (
              <div className="text-gray-500">暂无日志</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

// 辅助函数
function getAgentIcon(role) {
  const icons = {
    researcher: '🔹',
    coder: '💻',
    analyzer: '📊',
    writer: '✍️',
    reviewer: '✅'
  };
  return icons[role?.toLowerCase()] || '🔹';
}

function StatusBadge({ status }) {
  const statusConfig = {
    pending: { color: 'gray', text: '等待' },
    running: { color: 'blue', text: '进行中' },
    completed: { color: 'green', text: '完成' },
    failed: { color: 'red', text: '失败' }
  };

  const config = statusConfig[status] || statusConfig.pending;

  return (
    <span className={`text-xs px-2 py-0.5 rounded bg-${config.color}-100 text-${config.color}-800`}>
      {config.text}
    </span>
  );
}

export default AgentPanel;
