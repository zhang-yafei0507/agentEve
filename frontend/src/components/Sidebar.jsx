import React from 'react';
import { useStore } from '../store';
import { formatDistanceToNow } from 'date-fns';
import { zhCN } from 'date-fns/locale';

const Sidebar = () => {
  // 关键修复：使用选择器来获取状态
  const sessions = useStore((state) => state.sessions);
  const currentSessionId = useStore((state) => state.currentSessionId);
  const createSession = useStore((state) => state.createSession);
  const deleteSession = useStore((state) => state.deleteSession);
  const loadSessionHistory = useStore((state) => state.loadSessionHistory);
  const clearCurrentSession = useStore((state) => state.clearCurrentSession);

  const handleNewChat = async () => {
    console.log('[Sidebar] 点击新对话');
    // 关键修复：仅清空当前消息和会话 ID，保留历史会话列表
    clearCurrentSession();
    // 不创建新会话，让用户发送第一条消息时再创建
    console.log('[Sidebar] 状态已重置，准备显示欢迎页');
  };

  const handleSelectSession = async (sessionId) => {
    console.log('[Sidebar] 选择会话:', sessionId);
    try {
      // 调用 API 获取历史消息
      await loadSessionHistory(sessionId);
      console.log('[Sidebar] 会话加载完成:', sessionId);
    } catch (error) {
      console.error('[Sidebar] 加载会话失败:', error);
      alert('加载会话失败，请重试');
    }
  };

  const handleDeleteSession = async (e, sessionId) => {
    e.stopPropagation();
    if (window.confirm('确定要删除这个会话吗？')) {
      await deleteSession(sessionId);
    }
  };

  return (
    <div className="w-60 bg-white border-r border-gray-200 flex flex-col h-full">
      {/* Logo */}
      <div className="p-4 border-b border-gray-200">
        <h1 className="text-xl font-bold text-primary">🤖 Agent Eve</h1>
        <p className="text-xs text-gray-500 mt-1">Agentic RAG 协作系统</p>
      </div>

      {/* 新对话按钮 */}
      <div className="p-3">
        <button
          onClick={handleNewChat}
          className="w-full bg-primary text-white py-2 px-4 rounded-lg hover:bg-blue-600 transition-colors flex items-center justify-center gap-2"
        >
          <span>➕</span>
          <span>新对话</span>
        </button>
      </div>

      {/* 功能菜单 */}
      <div className="px-3 py-2 space-y-1">
        <button className="w-full text-left px-3 py-2 rounded-lg hover:bg-gray-100 transition-colors flex items-center gap-2">
          <span>🎨</span>
          <span>AI 创作</span>
        </button>
        <button className="w-full text-left px-3 py-2 rounded-lg hover:bg-gray-100 transition-colors flex items-center gap-2">
          <span>☁️</span>
          <span>云盘</span>
        </button>
        <button className="w-full text-left px-3 py-2 rounded-lg hover:bg-gray-100 transition-colors flex items-center gap-2">
          <span>⋯</span>
          <span>更多</span>
        </button>
      </div>

      {/* 历史对话 */}
      <div className="flex-1 overflow-y-auto px-3 py-2">
        <h3 className="text-xs text-gray-500 mb-2">📚 历史对话</h3>
        <div className="space-y-1">
          {sessions && sessions.length > 0 ? (
            sessions.map((session) => (
              <div
                key={session.id}
                onClick={() => handleSelectSession(session.id)}
                className={`group relative px-3 py-2 rounded-lg cursor-pointer transition-colors ${
                  currentSessionId === session.id
                    ? 'bg-blue-50 border-l-4 border-primary'
                    : 'hover:bg-gray-100'
                }`}
                role="button"
                tabIndex={0}
                aria-label={`选择会话：${session.title}`}
              >
                <div className="text-sm text-gray-700 truncate pr-6">
                  💬 {session.title}
                </div>
                <div className="text-xs text-gray-400 mt-1">
                  {formatDistanceToNow(new Date(session.updated_at), {
                    addSuffix: true,
                    locale: zhCN
                  })}
                </div>
                
                {/* 删除按钮 */}
                <button
                  onClick={(e) => handleDeleteSession(e, session.id)}
                  className="absolute right-2 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 transition-opacity text-red-500 hover:text-red-700"
                  title="删除会话"
                >
                  ✕
                </button>
              </div>
            ))
          ) : (
            <div className="text-center text-gray-400 text-xs py-4">
              暂无历史对话
            </div>
          )}
        </div>
      </div>

      {/* 用户信息 */}
      <div className="p-3 border-t border-gray-200">
        <div className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-gray-100 cursor-pointer">
          <div className="w-8 h-8 bg-primary rounded-full flex items-center justify-center text-white font-bold">
            U
          </div>
          <div className="flex-1">
            <div className="text-sm font-medium">用户</div>
            <div className="text-xs text-gray-500">user@example.com</div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Sidebar;
