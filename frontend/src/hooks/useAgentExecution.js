/**
 * 智能体执行 Hook
 * 封装 SSE 事件处理和执行逻辑
 */
import { useEffect, useCallback, useRef } from 'react';
import executionStore from '../store/executionStore';
import { chatAPI } from '../services/api';

export function useAgentExecution(sessionId) {
  const store = executionStore();
  const eventSourceRef = useRef(null);
  
  /**
   * 处理 SSE 事件
   */
  const handleSSEEvent = useCallback((event) => {
    console.log('[useAgentExecution] 收到事件:', event.type, event.data);
    
    switch (event.type) {
      case 'session_info':
        // 初始化会话
        store.startExecution(event.data.goal || '', event.data.execution_id);
        break;
        
      case 'supervisor_thought':
        // 添加思考记录
        store.addThought({
          step: event.data.step || 0,
          action: event.data.action || event.data.reasoning,
          reasoning: event.data.reasoning,
          tool: event.data.tool,
          tool_args: event.data.tool_args
        });
        break;
        
      case 'tool_call_start':
        // 添加工具调用（运行中）
        store.addToolCall({
          step: event.data.step || 0,
          tool: event.data.tool,
          params: event.data.params,
          status: 'running'
        });
        break;
        
      case 'tool_call_end':
        // 更新工具调用状态
        const toolCalls = store.getState().toolCalls;
        const lastToolIndex = toolCalls.findIndex(
          tc => tc.tool === event.data.tool && tc.status === 'running'
        );
        
        if (lastToolIndex >= 0) {
          store.updateToolCall(lastToolIndex, {
            status: event.data.status,
            result: event.data.result,
            endTime: new Date().toISOString()
          });
        } else {
          // 如果没有找到 running 状态的，直接添加
          store.addToolCall({
            step: event.data.step || 0,
            tool: event.data.tool,
            result: event.data.result,
            status: event.data.status,
            endTime: new Date().toISOString()
          });
        }
        break;
        
      case 'reflection':
        // 添加反思记录
        store.addReflection({
          step: event.data.step || 0,
          quality_score: event.data.quality_score,
          observation_summary: event.data.observation_summary,
          adjustment: event.data.adjustment,
          should_continue: event.data.should_continue,
          should_finish: event.data.should_finish
        });
        break;
        
      case 'final_answer_chunk':
        // 追加答案片段
        store.appendAnswer(event.data.chunk || '');
        break;
        
      case 'error':
        // 错误处理
        console.error('[Execution Error]', event.data);
        store.failExecution({
          error_type: event.data.error_type,
          message: event.data.message,
          recoverable: event.data.recoverable
        });
        break;
        
      case 'done':
        // 执行完成
        store.completeExecution(event.data);
        break;
        
      default:
        console.warn('未知事件类型:', event.type);
    }
  }, [store]);
  
  /**
   * 执行任务
   */
  const execute = useCallback(async (query) => {
    console.log('[useAgentExecution] 开始执行任务:', query);
    
    try {
      // 重置之前的状态
      store.resetExecution();
      
      // 开始执行
      store.startExecution(query);
      
      // 发送请求并处理 SSE 流
      await chatAPI.sendChatStream(
        query,
        sessionId,
        null,
        handleSSEEvent
      );
      
    } catch (error) {
      console.error('[Execution Failed]', error);
      store.failExecution({
        error_type: 'execution_error',
        message: error.message,
        recoverable: false
      });
    }
  }, [sessionId, handleSSEEvent, store]);
  
  /**
   * 停止执行
   */
  const stopExecution = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    store.failExecution({
      error_type: 'user_cancelled',
      message: '用户取消执行',
      recoverable: false
    });
  }, [store]);
  
  /**
   * 重置执行状态
   */
  const reset = useCallback(() => {
    store.resetExecution();
  }, [store]);
  
  return {
    // 执行方法
    execute,
    stopExecution,
    reset,
    
    // 当前状态
    thoughts: store.supervisorThoughts,
    taskPlan: store.taskPlan,
    toolCalls: store.toolCalls,
    reflections: store.reflections,
    finalAnswer: store.finalAnswer,
    stats: store.stats,
    
    // 执行状态
    status: store.currentExecution?.status || 'idle',
    goal: store.currentExecution?.goal,
    startTime: store.currentExecution?.startTime,
    endTime: store.currentExecution?.endTime,
    error: store.currentExecution?.error
  };
}
