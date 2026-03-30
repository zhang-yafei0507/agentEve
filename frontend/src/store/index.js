import { create } from 'zustand';
import api from '../services/api';

export const useStore = create((set, get) => ({
  // 会话相关
  sessions: [],
  currentSessionId: null,
  messages: [],
  
  // 智能体协作状态（已重构：与当前消息绑定）
  activeAgents: [],
  currentMessageId: null, // 跟踪当前正在流式传输的消息 ID
  
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
          // 新架构：确保 AI 消息有正确的 status 和结构化数据
          if (msg.role === 'assistant') {
            return {
              ...msg,
              status: msg.status || 'completed', // 默认完成状态
              // 从 msg_metadata 中提取或兼容旧字段
              supervisor_thoughts: msg.msg_metadata?.supervisor_thoughts || msg.thinking_process || [],
              reflections: msg.msg_metadata?.reflections || [],
              tool_calls: msg.msg_metadata?.tool_calls || [],
              // 已废弃但保留兼容性
              thinking_process: msg.thinking_process || [],
              sub_agent_results: msg.sub_agent_results || []
            };
          }
          return msg;
        })
      });
      
      // 关键修复：恢复最后一条 AI 消息的智能体状态到右侧面板（兼容性保留）
      const lastAiMessage = data.messages?.find(m => m.role === 'assistant' && m.supervisor_thoughts && m.supervisor_thoughts.length > 0);
      if (lastAiMessage && lastAiMessage.supervisor_thoughts) {
        console.log('[Store] 恢复智能体状态 from history:', lastAiMessage.supervisor_thoughts.length, '步思考');
        // 不再恢复到 activeAgents，因为新架构使用 supervisor_thoughts 直接展示
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
    
    // 关键修复：在函数开始处就检查重复
    const existingMessage = state.messages.find(
      m => m.role === 'user' && 
           m.content === query && 
           (Date.now() - new Date(m.timestamp).getTime()) < 10000
    );
    
    if (existingMessage) {
      console.warn('[Store] ❌ 检测到重复消息，直接返回');
      return; // 直接返回，不执行后续逻辑
    }
    
    set({ isStreaming: true, isLoading: true });
    
    // 生成唯一的临时 ID
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
      
      // 二次检查：防止在 set 回调期间被其他操作添加
      const doubleCheck = prevState.messages.find(
        m => m.role === 'user' && 
             m.content === query && 
             (Date.now() - new Date(m.timestamp).getTime()) < 10000
      );
      
      if (doubleCheck) {
        console.warn('[Store] ⚠️ 二次检查发现重复，跳过添加');
        return prevState; // 不重复添加
      }
      
      messageAdded = true;
      console.log('[Store] ✅ 添加用户消息到消息列表，ID:', tempMessageId);
      console.log('[Store] ✅ 新消息数量:', prevState.messages.length + 1);
      return {
        messages: [...prevState.messages, userMessage]
      };
    });
    
    console.log('[Store] ✅ 用户消息添加结果:', messageAdded ? '成功' : '失败（重复消息）');
    
    if (!messageAdded) {
      // 如果消息未添加（重复），直接返回
      set({ isStreaming: false, isLoading: false });
      return;
    }
    
    // 使用 Ref 模式维护流式状态（新架构）
    const streamState = {
      aiMessageId: null,
      accumulatedContent: '',
      messageCreated: false,
      // 新架构：使用 supervisor_thoughts, tool_calls, reflections
      supervisorThoughts: [],  // 主智能体思考
      taskPlan: null,          // 任务规划
      toolCalls: [],           // 工具调用记录
      reflections: [],         // 反思历史
      taskSteps: []            // 任务步骤状态
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
            
          } else if (data.type === 'supervisor_thought') {
            // 新增：主智能体思考过程
            console.log('[Store] supervisor_thought:', data.action, data.message);
            streamState.supervisorThoughts.push({
              action: data.action,
              message: data.message,
              step: data.step || null,
              timestamp: new Date().toISOString()
            });
            
            // 实时更新消息中的思考过程
            set(prevState => {
              const existingMsgIndex = prevState.messages.findIndex(
                m => m.id === streamState.aiMessageId
              );
              
              if (existingMsgIndex >= 0) {
                const newMessages = [...prevState.messages];
                newMessages[existingMsgIndex] = {
                  ...newMessages[existingMsgIndex],
                  supervisor_thoughts: [...streamState.supervisorThoughts],
                  status: 'streaming'
                };
                return { messages: newMessages };
              }
              return prevState;
            });
            
          } else if (data.type === 'supervisor_decision') {
            // 新增：主智能体决策
            console.log('[Store] supervisor_decision:', data.decision, data.message);
            streamState.supervisorThoughts.push({
              type: 'decision',
              decision: data.decision,
              message: data.message,
              reasoning: data.reasoning || '',
              timestamp: new Date().toISOString()
            });
            
          } else if (data.type === 'task_plan') {
            // 新增：任务规划（支持渐进式更新）
            console.log('[Store] task_plan:', data.total_steps, 'steps');
            
            // 初始化步骤状态
            streamState.taskPlan = {
              total_steps: data.total_steps,
              steps: (data.steps || []).map(step => ({
                ...step,
                status: step.status || 'pending',
                revealed: step.revealed !== undefined ? step.revealed : true
              })),
              timestamp: new Date().toISOString()
            };
            
            // 实时更新消息中的任务规划
            set(prevState => {
              const existingMsgIndex = prevState.messages.findIndex(
                m => m.id === streamState.aiMessageId
              );
              
              if (existingMsgIndex >= 0) {
                const newMessages = [...prevState.messages];
                newMessages[existingMsgIndex] = {
                  ...newMessages[existingMsgIndex],
                  task_plan: streamState.taskPlan,
                  status: 'streaming'
                };
                return { messages: newMessages };
              }
              return prevState;
            });
            
          } else if (data.type === 'task_plan_update') {
            // 新增：任务规划更新（逐步揭示步骤）
            console.log('[Store] task_plan_update:', data.new_step);
            if (streamState.taskPlan && data.new_step) {
              // 添加新揭示的步骤
              streamState.taskPlan.steps.push({
                ...data.new_step,
                revealed: true
              });
              
              // 实时更新消息中的任务规划
              set(prevState => {
                const existingMsgIndex = prevState.messages.findIndex(
                  m => m.id === streamState.aiMessageId
                );
                
                if (existingMsgIndex >= 0) {
                  const newMessages = [...prevState.messages];
                  newMessages[existingMsgIndex] = {
                    ...newMessages[existingMsgIndex],
                    task_plan: { ...streamState.taskPlan },
                    status: 'streaming'
                  };
                  return { messages: newMessages };
                }
                return prevState;
              });
            }
            
          } else if (data.type === 'tool_call_start') {
            // 工具调用开始 - 创建新的工具调用记录
            console.log('[Store] tool_call_start:', data.tool, data.step);
            const newToolCall = {
              tool: data.tool,
              agent_id: data.agent_id,
              step: data.step,
              status: 'running',
              params: data.params || {},
              start_time: new Date().toISOString(),
              result: null,
              duration: 0
            };
            streamState.toolCalls.push(newToolCall);
            
            // 实时更新消息中的工具调用列表
            set(prevState => {
              const existingMsgIndex = prevState.messages.findIndex(
                m => m.id === streamState.aiMessageId
              );
              
              if (existingMsgIndex >= 0) {
                const newMessages = [...prevState.messages];
                newMessages[existingMsgIndex] = {
                  ...newMessages[existingMsgIndex],
                  tool_calls: [...streamState.toolCalls],
                  status: 'streaming'
                };
                return { messages: newMessages };
              }
              return prevState;
            });
            
          } else if (data.type === 'tool_call_end') {
            // 工具调用结束 - 更新最后一个工具调用的状态
            console.log('[Store] tool_call_end:', data.tool, data.status);
            if (streamState.toolCalls.length > 0) {
              const lastToolCall = streamState.toolCalls[streamState.toolCalls.length - 1];
              lastToolCall.status = data.status;
              lastToolCall.result = data.result;
              lastToolCall.duration = data.duration;
              lastToolCall.end_time = new Date().toISOString();
              
              // 实时更新消息中的工具调用列表
              set(prevState => {
                const existingMsgIndex = prevState.messages.findIndex(
                  m => m.id === streamState.aiMessageId
                );
                
                if (existingMsgIndex >= 0) {
                  const newMessages = [...prevState.messages];
                  newMessages[existingMsgIndex] = {
                    ...newMessages[existingMsgIndex],
                    tool_calls: [...streamState.toolCalls],
                    status: 'streaming'
                  };
                  return { messages: newMessages };
                }
                return prevState;
              });
            }
                      
          } else if (data.type === 'next_step_decision') {
            // 新增：下一步决策事件
            console.log('[Store] next_step_decision:', data.message);
            streamState.supervisorThoughts.push({
              type: 'next_step',
              current_step: data.current_step,
              message: data.message,
              timestamp: new Date().toISOString()
            });
                      
            // 实时更新消息中的思考过程
            set(prevState => {
              const existingMsgIndex = prevState.messages.findIndex(
                m => m.id === streamState.aiMessageId
              );
                        
              if (existingMsgIndex >= 0) {
                const newMessages = [...prevState.messages];
                newMessages[existingMsgIndex] = {
                  ...newMessages[existingMsgIndex],
                  supervisor_thoughts: [...streamState.supervisorThoughts],
                  status: 'streaming'
                };
                return { messages: newMessages };
              }
              return prevState;
            });
                      
          } else if (data.type === 'supervisor_reflecting') {
            // 新增：主智能体反思事件
            console.log('[Store] supervisor_reflecting:', data.message);
            streamState.supervisorThoughts.push({
              type: 'reflecting',
              action: 'reflecting',
              step: data.step,
              message: data.message,
              timestamp: new Date().toISOString()
            });
                      
            // 实时更新消息中的思考过程
            set(prevState => {
              const existingMsgIndex = prevState.messages.findIndex(
                m => m.id === streamState.aiMessageId
              );
                        
              if (existingMsgIndex >= 0) {
                const newMessages = [...prevState.messages];
                newMessages[existingMsgIndex] = {
                  ...newMessages[existingMsgIndex],
                  supervisor_thoughts: [...streamState.supervisorThoughts],
                  status: 'streaming'
                };
                return { messages: newMessages };
              }
              return prevState;
            });
          } else if (data.type === 'reflection') {
            // 新增：反思事件 - ReAct 循环的核心
            console.log('[Store] 🤔 reflection:', data.quality_score, data.observation_summary);
            streamState.reflections.push({
              step: data.step || 0,
              quality_score: data.quality_score || 0,
              observation_summary: data.observation_summary || '',
              adjustment: data.adjustment || '',
              should_continue: data.should_continue || false,
              should_finish: data.should_finish || false,
              timestamp: new Date().toISOString()
            });
            
            // 实时更新消息中的反思历史
            set(prevState => {
              const existingMsgIndex = prevState.messages.findIndex(
                m => m.id === streamState.aiMessageId
              );
              
              if (existingMsgIndex >= 0) {
                const newMessages = [...prevState.messages];
                newMessages[existingMsgIndex] = {
                  ...newMessages[existingMsgIndex],
                  reflections: [...streamState.reflections],
                  status: 'streaming'
                };
                return { messages: newMessages };
              }
              return prevState;
            });
          } else if (data.type === 'agent_update') {
            console.log('[Store] agent_update:', data.agent_id);
            
            // 更新全局 activeAgents（兼容性保留）
            get().updateAgentState(data);
            
            // 记录当前消息 ID
            if (streamState.aiMessageId) {
              streamState.currentMessageId = streamState.aiMessageId;
            }
            
            // 已移除：不再累积 thinking_process 和 sub_agent_results
            // 新架构使用 supervisor_thoughts + reflections + tool_calls
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
                  // 新架构：使用 supervisor_thoughts, reflections, tool_calls
                  supervisor_thoughts: [...streamState.supervisorThoughts],
                  reflections: [...streamState.reflections],
                  tool_calls: [...streamState.toolCalls]
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
                      supervisor_thoughts: [...streamState.supervisorThoughts],
                      reflections: [...streamState.reflections],
                      tool_calls: [...streamState.toolCalls],
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
  
  // 更新智能体状态（已重构，移除 sharedBoard）
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
  
  // 已移除：updateSharedBoard（新架构不再需要）
  
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
