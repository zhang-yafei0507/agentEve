/**
 * 执行统计组件
 * 展示 ReAct 循环的执行效率和资源消耗
 */
import React from 'react';

const ExecutionStats = ({ stats }) => {
  if (!stats) return null;
  
  const {
    total_steps = 0,
    successful_tool_calls = 0,
    failed_tool_calls = 0,
    total_tokens = 0,
    duration = 0
  } = stats;
  
  // 计算成功率
  const total_tool_attempts = successful_tool_calls + failed_tool_calls;
  const success_rate = total_tool_attempts > 0 
    ? (successful_tool_calls / total_tool_attempts * 100).toFixed(0) 
    : 0;
  
  // 格式化时间
  const formatDuration = (seconds) => {
    if (seconds < 60) return `${seconds.toFixed(1)}秒`;
    const minutes = Math.floor(seconds / 60);
    const secs = (seconds % 60).toFixed(1);
    return `${minutes}分${secs}秒`;
  };
  
  // 格式化 token 数
  const formatTokens = (tokens) => {
    if (tokens >= 1000) return `${(tokens / 1000).toFixed(1)}k`;
    return tokens.toString();
  };
  
  return (
    <div className="mt-4 p-4 bg-gray-50 border border-gray-200 rounded-lg">
      <h4 className="font-medium text-gray-700 mb-3 flex items-center gap-2">
        <span className="text-lg">📊</span>
        执行统计
      </h4>
      
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {/* 总步数 */}
        <div className="bg-white p-3 rounded border border-gray-200">
          <div className="text-xs text-gray-500 mb-1">执行步数</div>
          <div className="text-2xl font-bold text-blue-600">{total_steps}</div>
          <div className="text-xs text-gray-400 mt-1">ReAct 循环次数</div>
        </div>
        
        {/* 工具调用成功率 */}
        <div className="bg-white p-3 rounded border border-gray-200">
          <div className="text-xs text-gray-500 mb-1">工具成功率</div>
          <div className={`text-2xl font-bold ${
            success_rate >= 80 ? 'text-green-600' : 
            success_rate >= 60 ? 'text-yellow-600' : 'text-red-600'
          }`}>
            {success_rate}%
          </div>
          <div className="text-xs text-gray-400 mt-1">
            {successful_tool_calls}/{total_tool_attempts} 成功
          </div>
        </div>
        
        {/* 总耗时 */}
        <div className="bg-white p-3 rounded border border-gray-200">
          <div className="text-xs text-gray-500 mb-1">总耗时</div>
          <div className="text-xl font-bold text-purple-600">
            {formatDuration(duration)}
          </div>
          <div className="text-xs text-gray-400 mt-1">
            {(duration / total_steps).toFixed(1)}秒/步
          </div>
        </div>
        
        {/* Token 消耗 */}
        <div className="bg-white p-3 rounded border border-gray-200">
          <div className="text-xs text-gray-500 mb-1">Token 消耗</div>
          <div className="text-xl font-bold text-orange-600">
            {formatTokens(total_tokens)}
          </div>
          <div className="text-xs text-gray-400 mt-1">LLM 调用量</div>
        </div>
      </div>
      
      {/* 失败详情（如果有） */}
      {failed_tool_calls > 0 && (
        <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded">
          <div className="flex items-center gap-2 text-red-700">
            <span className="text-lg">⚠️</span>
            <span className="font-medium">检测到 {failed_tool_calls} 次工具调用失败</span>
          </div>
          <p className="text-xs text-red-600 mt-1">
            系统已自动重试或调整策略，最终完成任务
          </p>
        </div>
      )}
    </div>
  );
};

export default ExecutionStats;
