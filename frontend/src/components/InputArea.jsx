import React, { useState, useRef } from 'react';
import { useStore } from '../store';
import ToolSelector from './ToolSelector';

const InputArea = ({ onTogglePanel }) => {
  // 关键修复：使用选择器来获取状态
  const sendMessage = useStore((state) => state.sendMessage);
  const selectedTools = useStore((state) => state.selectedTools);
  const loadTools = useStore((state) => state.loadTools);
  const tools = useStore((state) => state.tools);
  const currentSessionId = useStore((state) => state.currentSessionId);
  const messages = useStore((state) => state.messages);
  
  const [query, setQuery] = useState('');
  const [isFocused, setIsFocused] = useState(false);
  const [showToolPanel, setShowToolPanel] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const textareaRef = useRef(null);

  const handleSubmit = async (e) => {
    e.preventDefault(); // 必须阻止表单提交
    console.log('[InputArea] 提交消息:', query, 'sessionId:', currentSessionId);
    
    if (!query.trim() || isSending) {
      console.log('[InputArea] 跳过发送：', !query.trim() ? '内容空白' : '正在发送');
      return;
    }

    setIsSending(true);
    const originalQuery = query;
    setQuery(''); // 清空输入框

    try {
      await sendMessage(originalQuery, (event) => {
        console.log('[InputArea] SSE Event:', event);
      });
      console.log('[InputArea] 消息发送成功');
    } catch (error) {
      console.error('[InputArea] 发送消息失败:', error);
      // 不跳转，只显示错误提示
      alert('发送失败，请重试');
    } finally {
      setIsSending(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault(); // 阻止换行
      handleSubmit(e);
    }
  };

  return (
    <div className="border-t border-gray-200 bg-white p-4">
      {/* 工具栏 - 始终显示 */}
      <div className="mb-3 flex items-center gap-2 overflow-x-auto pb-2">
        <button
          onClick={() => setShowToolPanel(!showToolPanel)}
          className="px-3 py-1.5 bg-gray-100 rounded-lg text-sm hover:bg-gray-200 transition-colors whitespace-nowrap"
        >
          🔍 联网
        </button>
        <button className="px-3 py-1.5 bg-gray-100 rounded-lg text-sm hover:bg-gray-200 transition-colors whitespace-nowrap">
          📁 上传
        </button>
        <button className="px-3 py-1.5 bg-gray-100 rounded-lg text-sm hover:bg-gray-200 transition-colors whitespace-nowrap">
          🧮 代码
        </button>
        <button className="px-3 py-1.5 bg-gray-100 rounded-lg text-sm hover:bg-gray-200 transition-colors whitespace-nowrap">
          📊 数据分析
        </button>
        <button className="px-3 py-1.5 bg-gray-100 rounded-lg text-sm hover:bg-gray-200 transition-colors whitespace-nowrap">
          🎨 图像
        </button>
        <button className="px-3 py-1.5 bg-gray-100 rounded-lg text-sm hover:bg-gray-200 transition-colors whitespace-nowrap">
          📝 写作
        </button>
        <button
          onClick={onTogglePanel}
          className="px-3 py-1.5 bg-blue-100 text-primary rounded-lg text-sm hover:bg-blue-200 transition-colors whitespace-nowrap font-medium"
        >
          👁️ 协作流程
        </button>
      </div>

      {/* 输入框 - 发送按钮内置在右侧 */}
      <form onSubmit={handleSubmit} className="relative">
        <div
          className={`min-h-[56px] max-h-[200px] rounded-3xl border transition-all flex items-center ${
            isFocused
              ? 'border-primary ring-2 ring-blue-100'
              : 'border-gray-300'
          } bg-white px-4`}
        >
          <textarea
            ref={textareaRef}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onFocus={() => setIsFocused(true)}
            onBlur={() => setIsFocused(false)}
            onKeyPress={handleKeyPress}
            placeholder="发消息..."
            className="flex-1 w-full h-full min-h-[40px] max-h-[160px] resize-none outline-none text-gray-800 placeholder-gray-400 py-3 pr-3 bg-transparent"
            rows={1}
            style={{ minHeight: '40px' }}
          />
          
          {/* 发送按钮 - 固定在输入框右侧 */}
          <button
            type="submit"
            disabled={!query.trim() || isSending}
            className={`ml-3 w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 transition-colors ${
              query.trim() && !isSending
                ? 'bg-primary text-white hover:bg-blue-600'
                : 'bg-gray-200 text-gray-400 cursor-not-allowed'
            }`}
          >
            {isSending ? (
              <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
            ) : (
              '➤'
            )}
          </button>
        </div>

        {/* 字数统计 */}
        <div className="mt-2">
          <div className="text-xs text-gray-400">
            {query.trim() ? `${query.trim().length} 字` : ''}
          </div>
        </div>
      </form>

      {/* 使用新的 ToolSelector 组件 */}
      <ToolSelector isOpen={showToolPanel} onClose={() => setShowToolPanel(false)} />
    </div>
  );
};

export default InputArea;
