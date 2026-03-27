import React, { useState } from 'react';
import { marked } from 'marked';

const MessageBubble = ({ message }) => {
  const [showThinking, setShowThinking] = useState(true);
  const isUser = message.role === 'user';
  
  // 调试日志
  console.log('[MessageBubble] 渲染消息:', {
    id: message.id,
    role: message.role,
    content: message.content?.substring(0, 50) + (message.content?.length > 50 ? '...' : ''),
    contentLength: message.content?.length || 0,
    status: message.status
  });
  
  // 处理空内容或 undefined（关键修复）
  const content = message.content || '';
  
  // 关键修复：只有 streaming 状态且内容为空时才显示"加载中..."
  const displayContent = content.trim() === '' && !isUser && (message.status === 'streaming' || message.status === 'thinking')
    ? '加载中...'
    : content;
  
  // 开发环境：显示调试信息
  const isDevelopment = process.env.NODE_ENV === 'development';

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      {!isUser && (
        <div className="w-10 h-10 rounded-full bg-primary flex items-center justify-center text-white font-bold mr-3 flex-shrink-0">
          AI
        </div>
      )}
      
      <div
        className={`max-w-[75%] rounded-2xl p-4 ${
          isUser
            ? 'bg-primary text-white rounded-br-none'
            : 'bg-white border border-gray-200 rounded-bl-none'
        }`}
      >
        {/* 思考过程（仅 AI 消息且存在思考日志时） */}
        {!isUser && message.thinking_process && message.thinking_process.length > 0 && (
          <div className="mb-4 bg-gray-50 border border-gray-200 rounded-lg p-4">
            <button
              onClick={() => setShowThinking(!showThinking)}
              className="flex items-center justify-between w-full text-left"
            >
              <span className="font-medium text-gray-700">💭 思考过程 ({message.thinking_process.length} 步)</span>
              <span className="text-gray-400">{showThinking ? '▲' : '▼'}</span>
            </button>
            
            {showThinking && message.thinking_process && message.thinking_process.length > 0 && (
              <div className="mt-3 space-y-2">
                {message.thinking_process.map((thought, index) => (
                  <div key={index} className="flex items-start gap-2 text-sm">
                    <span className="text-gray-400 mt-1">{index + 1}.</span>
                    <div className="flex-1">
                      <div className="font-medium text-primary">{thought.agent}</div>
                      <div className="text-gray-600">{thought.action}</div>
                      {thought.tool_calls && (
                        <span className="text-xs text-gray-500">
                          (工具调用：{thought.tool_calls}次)
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* 消息内容 */}
        <div
          className={`prose prose-sm max-w-none ${
            isUser ? 'text-white' : 'text-gray-800'
          }`}
          dangerouslySetInnerHTML={{ __html: marked(displayContent) }}
        />
        
        {/* 调试信息（仅开发环境） */}
        {process.env.NODE_ENV === 'development' && !isUser && (
          <div className="mt-2 text-xs text-gray-400">
            ID: {message.id}<br/>
            内容长度：{content.length} | 状态：{message.status || 'streaming'}
          </div>
        )}

        {/* 子智能体结果（仅 AI 消息） */}
        {!isUser && message.sub_agent_results && message.sub_agent_results.length > 0 && (
          <div className="mt-4 space-y-3">
            {message.sub_agent_results.map((agent, index) => (
              <div
                key={index}
                className="bg-blue-50 border border-blue-200 rounded-lg p-3"
              >
                <div className="flex items-center justify-between mb-2">
                  <h4 className="font-medium text-primary">
                    🔹 {agent.role} 的输出
                  </h4>
                  <span className="text-xs text-gray-500">
                    耗时：{agent.duration?.toFixed(1)}s
                  </span>
                </div>
                <p className="text-sm text-gray-700">{agent.output}</p>
              </div>
            ))}
          </div>
        )}

        {/* 引用来源（仅 AI 消息） */}
        {!isUser && message.citations && message.citations.length > 0 && (
          <div className="mt-4 pt-4 border-t border-gray-200">
            <h4 className="text-sm font-medium text-gray-600 mb-2">🔹 来源：</h4>
            <div className="space-y-1">
              {message.citations.map((citation, index) => (
                <div key={index} className="text-xs text-gray-600">
                  [{index + 1}] {citation.title}
                  {citation.url && (
                    <a
                      href={citation.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="ml-2 text-primary hover:underline"
                    >
                      查看原文 →
                    </a>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {isUser && (
        <div className="w-10 h-10 rounded-full bg-gray-300 flex items-center justify-center text-gray-600 font-bold ml-3 flex-shrink-0">
          U
        </div>
      )}
    </div>
  );
};

export default MessageBubble;
