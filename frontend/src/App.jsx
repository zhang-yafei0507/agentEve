import React, { useState, useEffect } from 'react';
import Sidebar from './components/Sidebar';
import ChatArea from './components/ChatArea';
import InputArea from './components/InputArea';
import AgentPanel from './components/AgentPanel';
import { useStore } from './store';

function App() {
  const { sessions, currentSessionId, loadSessions, loadSessionHistory } = useStore();
  const [showAgentPanel, setShowAgentPanel] = useState(false);
  const [initialized, setInitialized] = useState(false);

  console.log('[App] render - currentSessionId:', currentSessionId, 'sessions:', sessions.length);

  // 初始化时加载会话列表
  useEffect(() => {
    const initApp = async () => {
      console.log('[App] 初始化应用');
      await loadSessions();
      
      // 检查 URL 中的 sessionId
      const urlParams = new URLSearchParams(window.location.search);
      const sessionIdFromUrl = urlParams.get('session');
      
      if (sessionIdFromUrl) {
        console.log('[App] 从 URL 加载会话:', sessionIdFromUrl);
        try {
          await loadSessionHistory(sessionIdFromUrl);
        } catch (error) {
          console.error('[App] 从 URL 加载会话失败:', error);
        }
      }
      
      setInitialized(true);
      console.log('[App] 初始化完成');
    };
    
    initApp();
  }, []);

  return (
    <div className="flex h-screen bg-gray-50">
      {/* 左侧边栏 */}
      <Sidebar />

      {/* 中间主区域 */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* 聊天区域 */}
        <ChatArea />

        {/* 输入区域 */}
        <InputArea onTogglePanel={() => setShowAgentPanel(!showAgentPanel)} />
      </div>

      {/* 右侧智能体协作面板 */}
      {showAgentPanel && <AgentPanel onClose={() => setShowAgentPanel(false)} />}
    </div>
  );
}

export default App;
