/**
 * 智能体执行状态管理 Store
 * 使用 Zustand 管理 ReAct 循环的执行状态
 */
import { create } from 'zustand';

const executionStore = create((set, get) => ({
  // ========== 当前执行状态 ==========
  currentExecution: null,  // { id, goal, status, startTime }
  
  // ========== 结构化数据 ==========
  supervisorThoughts: [],      // 思考历史
  taskPlan: null,             // 任务规划（如有）
  toolCalls: [],              // 工具调用历史
  reflections: [],            // 反思历史
  finalAnswer: '',            // 最终答案
  
  // ========== 执行统计 ==========
  stats: {
    totalSteps: 0,
    successfulToolCalls: 0,
    failedToolCalls: 0,
    totalTokens: 0,
    duration: 0
  },
  
  // ========== 状态更新方法 ==========
  
  /**
   * 开始执行
   */
  startExecution: (goal, executionId = null) => set({
    currentExecution: {
      id: executionId || Date.now(),
      goal,
      status: 'running',
      startTime: new Date().toISOString()
    },
    supervisorThoughts: [],
    taskPlan: null,
    toolCalls: [],
    reflections: [],
    finalAnswer: '',
    stats: {
      totalSteps: 0,
      successfulToolCalls: 0,
      failedToolCalls: 0,
      totalTokens: 0,
      duration: 0
    }
  }),
  
  /**
   * 添加思考记录
   */
  addThought: (thought) => set((state) => ({
    supervisorThoughts: [
      ...state.supervisorThoughts,
      {
        ...thought,
        timestamp: new Date().toISOString()
      }
    ],
    stats: {
      ...state.stats,
      totalSteps: state.stats.totalSteps + 1
    }
  })),
  
  /**
   * 添加工具调用
   */
  addToolCall: (toolCall) => set((state) => {
    const isRunning = toolCall.status === 'running';
    return {
      toolCalls: [
        ...state.toolCalls,
        {
          ...toolCall,
          startTime: isRunning ? new Date().toISOString() : toolCall.startTime,
          endTime: !isRunning ? new Date().toISOString() : toolCall.endTime
        }
      ],
      stats: {
        ...state.stats,
        successfulToolCalls: state.stats.successfulToolCalls + (toolCall.status === 'success' ? 1 : 0),
        failedToolCalls: state.stats.failedToolCalls + (toolCall.status === 'failed' ? 1 : 0)
      }
    };
  }),
  
  /**
   * 更新工具调用状态
   */
  updateToolCall: (index, updates) => set((state) => ({
    toolCalls: state.toolCalls.map((tc, i) => 
      i === index ? { ...tc, ...updates } : tc
    )
  })),
  
  /**
   * 添加反思记录
   */
  addReflection: (reflection) => set((state) => ({
    reflections: [
      ...state.reflections,
      {
        ...reflection,
        timestamp: new Date().toISOString()
      }
    ]
  })),
  
  /**
   * 追加答案片段
   */
  appendAnswer: (chunk) => set((state) => ({
    finalAnswer: state.finalAnswer + chunk
  })),
  
  /**
   * 完成执行
   */
  completeExecution: (doneData) => set((state) => ({
    currentExecution: {
      ...state.currentExecution,
      status: 'completed',
      endTime: new Date().toISOString()
    },
    stats: {
      ...state.stats,
      totalSteps: doneData?.current_step || state.stats.totalSteps,
      totalTokens: doneData?.total_tokens || state.stats.totalTokens,
      duration: doneData?.duration || state.stats.duration
    }
  })),
  
  /**
   * 执行失败
   */
  failExecution: (error) => set((state) => ({
    currentExecution: {
      ...state.currentExecution,
      status: 'failed',
      error,
      endTime: new Date().toISOString()
    }
  })),
  
  /**
   * 重置状态
   */
  resetExecution: () => set({
    currentExecution: null,
    supervisorThoughts: [],
    taskPlan: null,
    toolCalls: [],
    reflections: [],
    finalAnswer: '',
    stats: {
      totalSteps: 0,
      successfulToolCalls: 0,
      failedToolCalls: 0,
      totalTokens: 0,
      duration: 0
    }
  })
}));

export default executionStore;
