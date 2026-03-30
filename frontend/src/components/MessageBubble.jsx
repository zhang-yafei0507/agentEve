import React, { useState } from 'react';
import { marked } from 'marked';
import SupervisorThoughtCard from './SupervisorThoughtCard';
import TaskPlanCard from './TaskPlanCard';
import ToolCallCard from './ToolCallCard';
// 新增：反思历史和执行统计组件
import ReflectionTimeline from './ReflectionTimeline';
import ExecutionStats from './ExecutionStats';

const MessageBubble = ({ message }) => {
  const [showThinking, setShowThinking] = useState(true);
  const [displayedContent, setDisplayedContent] = useState('');
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
  
  // 打字机效果：流式输出最终答案
  React.useEffect(() => {
    if (!content || isUser) {
      setDisplayedContent(content);
      return;
    }
    
    // 如果是流式状态，逐字显示
    if (message.status === 'streaming') {
      let currentIndex = 0;
      const interval = setInterval(() => {
        if (currentIndex < content.length) {
          // 每次显示 1-3 个字符（中文环境下更自然）
          const chunkSize = Math.min(3, content.length - currentIndex);
          currentIndex += chunkSize;
          setDisplayedContent(content.substring(0, currentIndex));
        } else {
          clearInterval(interval);
        }
      }, 20); // 20ms 显示一次，约 50 字/秒
      
      return () => clearInterval(interval);
    } else {
      // 已完成状态，直接显示全部内容
      setDisplayedContent(content);
    }
  }, [content, message.status, isUser]);
  
  // 计算已完成的步骤数（用于任务规划进度）
  const completedSteps = message.supervisor_thoughts?.length || 0;
  
  // 从消息中提取 reflections（新增）
  const reflections = message.reflections || [];

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
        {/* 思考过程卡片 - 已重构为 SupervisorThoughtCard */}
        {!isUser && message.supervisor_thoughts && message.supervisor_thoughts.length > 0 && (
          <SupervisorThoughtCard thoughts={message.supervisor_thoughts} />
        )}

        {/* 反思历史（新增） */}
        {!isUser && reflections && reflections.length > 0 && (
          <ReflectionTimeline reflections={reflections} />
        )}
        
        {/* 消息内容 */}
        <div
          className={`prose prose-sm max-w-none ${
            isUser ? 'text-white' : 'text-gray-800'
          }`}
          dangerouslySetInnerHTML={{ __html: marked(displayedContent) }}
        />
        
        {/* 流式光标（仅 streaming 状态） */}
        {message.status === 'streaming' && !isUser && (
          <span className="inline-block w-2 h-5 bg-blue-500 ml-1 animate-pulse"></span>
        )}
        
        {/* 调试信息（仅开发环境） */}
        {process.env.NODE_ENV === 'development' && !isUser && (
          <div className="mt-2 text-xs text-gray-400">
            ID: {message.id}<br/>
            内容长度：{content.length} | 状态：{message.status || 'streaming'}
          </div>
        )}

        {/* 执行统计（完成后显示，新增） */}
        {message.status === 'completed' && message.msg_metadata && (
          <ExecutionStats stats={{
            total_steps: message.msg_metadata.total_steps || 0,
            successful_tool_calls: message.msg_metadata.total_tool_calls || 0,
            failed_tool_calls: 0,
            total_tokens: message.msg_metadata.total_tokens || 0,
            duration: message.msg_metadata.duration || 0
          }} />
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
