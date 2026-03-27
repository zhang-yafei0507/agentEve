import React, { useRef, useEffect } from 'react';
import { useStore } from '../store';
import MessageBubble from './MessageBubble';

const ChatArea = () => {
  // 关键修复：使用选择器来获取状态，确保组件正确订阅
  const messages = useStore((state) => state.messages);
  const isStreaming = useStore((state) => state.isStreaming);
  const messagesEndRef = useRef(null);
  
  console.log('[ChatArea] ⚠️ 关键：render - messages count:', messages?.length || 0);
  console.log('[ChatArea] ⚠️ 关键：messages 数组引用:', messages);
  console.log('[ChatArea] messages:', messages?.map(m => ({
    id: m.id,
    role: m.role,
    contentLength: m.content?.length || 0,
    status: m.status
  })));

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    console.log('[ChatArea] scrollToBottom triggered');
    scrollToBottom();
  }, [messages, isStreaming]);

  // 空消息列表显示欢迎页
  if (!messages || messages.length === 0) {
    console.log('[ChatArea] 显示欢迎页');
    return (
      <div className="flex-1 flex items-center justify-center bg-gray-50">
        <div className="text-center max-w-2xl px-4">
          <h1 className="text-4xl font-bold text-gray-800 mb-8">
            🤖 有什么我能帮你的吗？
          </h1>
          
          {/* 快捷提问卡片 */}
          <div className="grid grid-cols-3 gap-4">
            {[
              '资讯：苹果 iPhone 16 发布',
              '分析午睡 20 分钟的好处',
              '如何训练自己的专注力',
              '帮我查询 95 号油价',
              '资讯：梦之墨演唱会',
              '在家做什么可以减肥',
              '用 C++ 编写排序算法',
              '告诉我黄金降价信息',
              '资讯：乌克兰局势更新'
            ].map((suggestion, index) => (
              <button
                key={index}
                className="bg-white p-4 rounded-lg border border-gray-200 hover:bg-blue-50 hover:border-primary transition-all text-left text-sm text-gray-700 h-20 flex items-center"
              >
                {suggestion}
              </button>
            ))}
          </div>
        </div>
      </div>
    );
  }

  // 有消息时显示消息列表
  console.log('[ChatArea] 显示消息列表，数量:', messages.length);
  return (
    <div className="flex-1 overflow-y-auto bg-gray-50 p-4">
      <div className="max-w-4xl mx-auto space-y-4">
        {messages.map((message) => {
          console.log('[ChatArea] rendering message:', {
            id: message.id,
            role: message.role,
            contentLength: message.content?.length || 0
          });
          return (
            <MessageBubble key={message.id} message={message} />
          );
        })}
        
        {/* 加载中提示 */}
        {isStreaming && (
          <div className="flex items-center gap-2 text-gray-500">
            <div className="w-2 h-2 bg-primary rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
            <div className="w-2 h-2 bg-primary rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
            <div className="w-2 h-2 bg-primary rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>
    </div>
  );
};

export default ChatArea;
