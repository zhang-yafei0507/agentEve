import React, { useRef, useEffect } from 'react';
import { useStore } from '../store';
import MessageBubble from './MessageBubble';
import EmptyState from './EmptyState';

const ChatArea = () => {
  // 关键修复：使用选择器来获取状态，确保组件正确订阅
  const messages = useStore((state) => state.messages);
  const isStreaming = useStore((state) => state.isStreaming);
  const sendMessage = useStore((state) => state.sendMessage);
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
    
    // 处理快捷提问点击
    const handleQuickAsk = async (question) => {
      console.log('[ChatArea] 快捷提问:', question);
      try {
        await sendMessage(question);
      } catch (error) {
        console.error('[ChatArea] 发送消息失败:', error);
      }
    };
    
    return <EmptyState onQuickAsk={handleQuickAsk} />;
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
