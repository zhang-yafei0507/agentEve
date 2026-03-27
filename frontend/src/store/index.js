import { create } from 'zustand';
import api from '../services/api';

export const useStore = create((set, get) => ({
  // 会话相关
  sessions: [],
  currentSessionId: null,
  messages: [],
  
  // 智能体协作状态
  activeAgents: [],
  sharedBoard: {
    key_findings: [],
    intermediate_conclusions: [],
    open_questions: [],
    help_requests: []
  },
  
  // 工具相关
  tools: [],
  selectedTools: [],
  
  // 加载状态
  isLoading: false,
  isStreaming: false,
  
  // 获取会话列表
  loadSessions: async () => {
    try {
      const data = await api.getSessions();
      set({ sessions: data.sessions });
    } catch (error) {
      console.error('加载会话失败:', error);
    }
  },
  
  // 创建新会话
  createSession: async (title) => {
    try {
      const data = await api.createSession(title);
      const newSession = data.session;
      set(state => ({
        sessions: [newSession, ...state.sessions],
        currentSessionId: newSession.id,
        messages: []
      }));
      return newSession;
    } catch (error) {
      console.error('创建会话失败:', error);
      return null;
    }
  },
  
  // 删除会话
  deleteSession: async (sessionId) => {
    try {
      await api.deleteSession(sessionId);
      set(state => ({
        sessions: state.sessions.filter(s => s.id !== sessionId),
        currentSessionId: state.currentSessionId === sessionId ? null : state.currentSessionId
      }));
    } catch (error) {
      console.error('删除会话失败:', error);
    }
  },
  
  // 加载会话历史（关键修复：保护 streaming 状态的消息）
  loadSessionHistory: async (sessionId) => {
    console.log('[Store] loadSessionHistory - sessionId:', sessionId);
    try {
      // 调用 chat API 获取历史消息（已重定向）
      const data = await api.getSessionHistory(sessionId);
      console.log('[Store] 收到历史消息:', data.messages?.length || 0, '条');
      
      // 关键修复：保护正在流式传输的消息
      const currentState = get();
      const streamingMessages = currentState.messages.filter(m => m.status === 'streaming' || m.status === 'thinking');
      
      if (streamingMessages.length > 0) {
        console.log('[Store] 检测到 streaming 消息，跳过历史加载以避免覆盖');
        // 只更新 currentSessionId，不覆盖 messages
        set({ currentSessionId: sessionId });
        return;
      }
      
      set({
        currentSessionId: sessionId,
        messages: (data.messages || []).map(msg => {
          // 关键修复：确保 AI 消息有正确的 status
          if (msg.role === 'assistant') {
            return {
              ...msg,
              status: msg.status || 'completed', // 默认完成状态
              thinking_process: msg.thinking_process || [],
              sub_agent_results: msg.sub_agent_results || [],
              citations: msg.citations || []
            };
          }
          return msg;
        })
      });
      
      // 关键修复：恢复最后一条 AI 消息的智能体状态到右侧面板
      const lastAiMessage = data.messages?.find(m => m.role === 'assistant' && m.sub_agent_results && m.sub_agent_results.length > 0);
      if (lastAiMessage && lastAiMessage.sub_agent_results) {
        console.log('[Store] 恢复智能体状态 from history:', lastAiMessage.sub_agent_results.length, 'agents');
        // 将子智能体结果恢复到 activeAgents
        lastAiMessage.sub_agent_results.forEach(agentResult => {
          get().updateAgentState({
            agent_id: agentResult.agent_id,
            role: agentResult.role,
            status: 'completed',
            message: agentResult.output,
            task: agentResult.task,
            duration: agentResult.duration,
            tool_calls: agentResult.tool_calls
          });
        });
      }
    } catch (error) {
      console.error('[Store] 加载历史失败:', error);
      throw error;
    }
  },
  
  // 发送消息（流式）
  sendMessage: async (query, onEvent) => {
    const state = get();
    console.log('[Store] sendMessage - query:', query, 'sessionId:', state.currentSessionId);
    
    set({ isStreaming: true, isLoading: true });
    
    // 关键修复：生成唯一的临时 ID，避免重复
    const tempMessageId = `user-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    
    // 乐观更新用户消息到本地（带唯一 ID）
    const userMessage = {
      id: tempMessageId,
      role: 'user',
      content: query,
      timestamp: new Date().toISOString()
    };
    
    console.log('[Store] ⚠️ 关键：准备添加用户消息:', userMessage);
    console.log('[Store] ⚠️ 关键：当前消息数量:', state.messages.length);
    
    // 关键修复：使用函数形式的 set，确保获取最新状态
    let messageAdded = false;
    set(prevState => {
      console.log('[Store] ⚠️ 关键：set 回调中的 prevState.messages.length =', prevState.messages.length);
      
      // 防止重复：检查是否已存在相同内容的消息（10 秒内）
      const existingMessage = prevState.messages.find(
        m => m.role === 'user' && 
             m.content === query && 
             (Date.now() - new Date(m.timestamp).getTime()) < 10000
      );
      
      if (existingMessage) {
        console.warn('[Store] 检测到重复消息，跳过添加');
        return prevState; // 不重复添加
      }
      
      messageAdded = true;
      console.log('[Store] ✅ 添加用户消息到消息列表，ID:', tempMessageId);
      console.log('[Store] ✅ 新消息数量:', prevState.messages.length + 1);
      return {
        messages: [...prevState.messages, userMessage]
      };
    });
    
    console.log('[Store] ✅ 用户消息添加结果:', messageAdded ? '成功' : '失败（可能是重复消息）');
    
    // 使用 Ref 模式维护流式状态（关键修复）
    const streamState = {
      aiMessageId: null,
      accumulatedContent: '',
      messageCreated: false,
      // 关键修复：实时累积结构化数据
      thinkingProcess: [],
      subAgentResults: []
    };
    
    try {
      // 使用 fetch 接收 SSE
      await api.sendChatStream(
        query,
        state.currentSessionId,
        state.selectedTools,
        (data) => {
          console.log('[Store] 收到 SSE 数据:', data.type, data);
          
          // 处理接收到的数据
          if (onEvent) {
            onEvent(data);
          }
          
          // 根据事件类型更新状态
          if (data.type === 'session_info') {
            console.log('[Store] 收到 session_info:', data);
            console.log('[Store] ⚠️ 关键：后端返回的 message_id =', data.message_id);
            // 关键修复：保存真实的 message_id 并锁定
            streamState.aiMessageId = data.message_id;
            streamState.accumulatedContent = '';
            streamState.messageCreated = false;
            set({ currentSessionId: data.session_id });
            
          } else if (data.type === 'agent_update') {
            console.log('[Store] agent_update:', data.agent_id);
            get().updateAgentState(data);
            
            // 关键修复：实时累积思考过程和子智能体结果
            if (data.status === 'completed' && data.output) {
              // 添加到 thinking_process
              streamState.thinkingProcess.push({
                agent: data.agent || data.role,
                action: data.task || '',
                tool_calls: data.tool_calls || 0,
                duration: data.duration || 0,
                timestamp: new Date().toISOString()
              });
              
              // 添加到 sub_agent_results
              streamState.subAgentResults.push({
                agent_id: data.agent_id,
                role: data.agent || data.role,
                task: data.task,
                output: data.output,
                tool_calls: data.tool_calls || 0,
                duration: data.duration || 0
              });
              
              console.log('[Store] ✅ 累积结构化数据:', {
                thinking_process: streamState.thinkingProcess.length,
                sub_agent_results: streamState.subAgentResults.length
              });
            }
            
          } else if (data.type === 'tool_call_start' || data.type === 'tool_call_result') {
            // 工具调用事件
            console.log('[Store] 工具调用:', data.tool_name);
            
          } else if (data.type === 'final_answer_chunk') {
            // 答案片段 - 累积内容（关键修复）
            const chunk = data.chunk || '';
            streamState.accumulatedContent += chunk;
            console.log('[Store] final_answer_chunk 累积:', streamState.accumulatedContent.length, '当前 chunk:', chunk);
            console.log('[Store] ⚠️ 关键：aiMessageId =', streamState.aiMessageId);
            
            // 关键修复：确保 aiMessageId 存在
            if (!streamState.aiMessageId) {
              console.error('[Store] ❌ 错误：收到 chunk 但 aiMessageId 为空！');
              return;
            }
            
            // 实时更新 assistant 消息（使用锁定的 aiMessageId）
            set(prevState => {
              console.log('[Store] 更新 AI 消息内容，当前消息数:', prevState.messages.length);
              
              const existingMsgIndex = prevState.messages.findIndex(
                m => m.id === streamState.aiMessageId
              );
              
              console.log('[Store] ⚠️ 关键：查找 AI 消息 - aiMessageId:', streamState.aiMessageId, '找到索引:', existingMsgIndex);
              
              if (existingMsgIndex >= 0) {
                // 更新现有消息（创建新对象引用）
                const newMessages = [...prevState.messages];
                newMessages[existingMsgIndex] = {
                  ...newMessages[existingMsgIndex],
                  content: streamState.accumulatedContent,
                  status: 'streaming',
                  // 关键修复：实时更新结构化字段
                  thinking_process: [...streamState.thinkingProcess],
                  sub_agent_results: [...streamState.subAgentResults]
                };
                console.log('[Store] ✅ 成功更新消息内容和结构化数据');
                return { messages: newMessages };
              } else {
                // 未找到消息，创建新消息
                console.warn('[Store] ❌ 未找到 AI 消息，创建新消息');
                return {
                  messages: [
                    ...prevState.messages,
                    {
                      id: streamState.aiMessageId,
                      role: 'assistant',
                      content: streamState.accumulatedContent,
                      thinking_process: [...streamState.thinkingProcess],
                      sub_agent_results: [...streamState.subAgentResults],
                      citations: [],
                      status: 'streaming',
                      timestamp: new Date().toISOString()
                    }
                  ]
                };
              }
            });
          } else if (data.type === 'done') {
            console.log('[Store] 流式传输完成，最终内容长度:', streamState.accumulatedContent.length);
            // 关键修复：done 事件只标记完成状态，不再更新结构化数据
            set(prevState => {
              const newMessages = [...prevState.messages];
              const aiMsgIndex = newMessages.findIndex(m => m.id === streamState.aiMessageId);
              if (aiMsgIndex >= 0) {
                newMessages[aiMsgIndex] = {
                  ...newMessages[aiMsgIndex],
                  status: 'completed'
                };
              }
              return { messages: newMessages };
            });
            
            console.log('[Store] ✅ 流式传输完成，结构化数据已在之前同步');
          } else if (data.type === 'error') {
            console.error('[Store] 错误:', data.error);
            throw new Error(data.error);
          }
        }
      );
      
      // 关键修复：移除自动加载历史的逻辑
      // 历史消息将在用户切换会话或刷新页面时才加载
      console.log('[Store] 流式传输结束，保持当前内容到本地');
      
    } catch (error) {
      console.error('[Store] ❌ 发送消息失败:', error);
      console.error('[Store] ❌ 错误堆栈:', error.stack);
      // 发生错误时移除未完成的消息
      console.log('[Store] ⚠️ 准备移除用户消息，内容:', query);
      set(prevState => {
        const beforeCount = prevState.messages.length;
        const newMessages = prevState.messages.filter(m => m.content !== query);
        console.log('[Store] ⚠️ 移除后消息数量:', beforeCount, '→', newMessages.length);
        return { messages: newMessages };
      });
      throw error;
    } finally {
      console.log('[Store] 重置流式状态');
      console.log('[Store] ⚠️ 关键：最终消息数量:', get().messages.length);
      set({ isStreaming: false, isLoading: false });
    }
  },
  
  // 更新智能体状态
  updateAgentState: (agentUpdate) => {
    console.log('[Store] updateAgentState:', agentUpdate);
    set(state => {
      const existingIndex = state.activeAgents.findIndex(
        a => a.agent_id === agentUpdate.agent_id
      );
      
      let newAgents;
      if (existingIndex >= 0) {
        // 更新现有智能体（合并所有字段）
        newAgents = [...state.activeAgents];
        newAgents[existingIndex] = { 
          ...newAgents[existingIndex], 
          ...agentUpdate,
          // 确保这些字段总是存在
          task: agentUpdate.task || newAgents[existingIndex].task,
          tools: agentUpdate.tools || newAgents[existingIndex].tools,
          tool_calls: agentUpdate.tool_calls !== undefined ? agentUpdate.tool_calls : newAgents[existingIndex].tool_calls,
          duration: agentUpdate.duration || newAgents[existingIndex].duration
        };
        console.log('[Store] 更新智能体状态:', newAgents[existingIndex]);
      } else {
        // 添加新智能体
        newAgents = [...state.activeAgents, {
          ...agentUpdate,
          // 确保有必要的字段
          task: agentUpdate.task || '',
          tools: agentUpdate.tools || [],
          tool_calls: agentUpdate.tool_calls !== undefined ? agentUpdate.tool_calls : 0,
          duration: agentUpdate.duration || 0
        }];
        console.log('[Store] 添加新智能体:', newAgents[newAgents.length - 1]);
      }
      
      return { activeAgents: newAgents };
    });
  },
  
  // 更新共享状态板
  updateSharedBoard: (update) => {
    set(state => ({
      sharedBoard: {
        ...state.sharedBoard,
        ...update
      }
    }));
  },
  
  // 加载工具列表
  loadTools: async () => {
    try {
      const data = await api.getTools();
      set({ tools: data.tools });
    } catch (error) {
      console.error('加载工具失败:', error);
    }
  },
  
  // 切换工具选择
  toggleTool: (toolId) => {
    set(state => {
      const isSelected = state.selectedTools.includes(toolId);
      return {
        selectedTools: isSelected
          ? state.selectedTools.filter(id => id !== toolId)
          : [...state.selectedTools, toolId]
      };
    });
  },
  
  // 清空当前会话
  clearCurrentSession: () => {
    set({
      currentSessionId: null,
      messages: [],
      activeAgents: [],
      sharedBoard: {
        key_findings: [],
        intermediate_conclusions: [],
        open_questions: [],
        help_requests: []
      }
    });
  }
}));
