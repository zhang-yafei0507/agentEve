import axios from 'axios';

const API_BASE_URL = '/api';

// 创建 axios 实例
const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 聊天相关 API
export const chatAPI = {
  // 发送消息（SSE 流式）
  sendChatStream: async (query, sessionId, selectedTools, onMessage) => {
    const params = new URLSearchParams();
    params.append('query', query);
    if (sessionId) params.append('session_id', sessionId);
    if (selectedTools && selectedTools.length > 0) {
      params.append('selected_tools', JSON.stringify(selectedTools));
    }
    
    console.log('[API] 发送 SSE 请求:', `${API_BASE_URL}/chat/send?${params.toString()}`);
    
    // 使用 fetch 支持 POST 的 SSE
    const response = await fetch(`${API_BASE_URL}/chat/send?${params.toString()}`, {
      method: 'POST',
      headers: {
        'Accept': 'text/event-stream',
      },
    });
    
    if (!response.ok) {
      const errorText = await response.text();
      console.error('[API] SSE 请求失败:', response.status, errorText);
      throw new Error(`HTTP error! status: ${response.status}, message: ${errorText}`);
    }
    
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let chunkCount = 0;
    
    console.log('[API] 开始读取 SSE 流...');
    
    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) {
          console.log('[API] SSE 流结束，接收 chunk 数:', chunkCount);
          break;
        }
        
        // 解码并累积到缓冲区
        const text = decoder.decode(value, { stream: true });
        console.log('[API] 收到原始数据:', text.substring(0, 200) + (text.length > 200 ? '...' : ''));
        
        buffer += text;
        chunkCount++;
        
        // 按行分割处理
        const lines = buffer.split('\n');
        buffer = lines.pop(); // 保留最后一行可能不完整的行
        
        console.log('[API] 分割后的行数:', lines.length);
        
        for (const line of lines) {
          const trimmedLine = line.trim();
          
          // 跳过空行和注释
          if (!trimmedLine || trimmedLine.startsWith(':')) {
            continue;
          }
          
          // 处理 data: 前缀
          if (trimmedLine.startsWith('data: ')) {
            const data = trimmedLine.slice(6); // 移除 'data: ' 前缀
            console.log('[API] 解析 data 内容:', data.substring(0, 100) + (data.length > 100 ? '...' : ''));
            
            try {
              const parsed = JSON.parse(data);
              console.log('[API] 解析成功，类型:', parsed.type);
              if (onMessage) {
                onMessage(parsed);
              }
            } catch (e) {
              console.error('[API] 解析 JSON 失败:', e, 'data:', data);
            }
          } else if (trimmedLine === 'data:') {
            // 处理空的 data 标记（表示流结束）
            console.log('[API] 收到空 data 标记');
          } else {
            console.log('[API] 未知格式的行:', trimmedLine.substring(0, 50));
          }
        }
      }
    } catch (error) {
      console.error('[API] 读取 SSE 流失败:', error);
      throw error;
    } finally {
      reader.releaseLock();
    }
  },
  
  // 获取会话历史
  getHistory: async (sessionId) => {
    console.log('[API] getHistory - sessionId:', sessionId);
    const response = await api.get(`/chat/history/${sessionId}`);
    console.log('[API] 收到历史消息:', response.data);
    return response.data;
  },
};

// 会话相关 API
export const sessionAPI = {
  // 获取会话列表
  list: async () => {
    const response = await api.get('/sessions/list');
    return response.data;
  },
  
  // 获取会话详情
  get: async (sessionId) => {
    const response = await api.get(`/sessions/${sessionId}`);
    return response.data;
  },
  
  // 创建会话
  create: async (title) => {
    const response = await api.post('/sessions/create', { title });
    return response.data;
  },
  
  // 删除会话
  delete: async (sessionId) => {
    const response = await api.delete(`/sessions/${sessionId}`);
    return response.data;
  },
  
  // 重命名会话
  rename: async (sessionId, title) => {
    const response = await api.put(`/sessions/${sessionId}/rename`, { title });
    return response.data;
  },
  
  // 导出会话
  export: async (sessionId, format = 'markdown') => {
    const response = await api.get(`/sessions/${sessionId}/export?format=${format}`);
    return response.data;
  },
};

// 工具相关 API
export const toolAPI = {
  // 获取工具列表
  list: async (category, enabledOnly) => {
    const params = {};
    if (category) params.category = category;
    if (enabledOnly) params.enabled_only = true;
    
    const response = await api.get('/tools/list', { params });
    return response.data;
  },
  
  // 获取工具详情
  get: async (toolId) => {
    const response = await api.get(`/tools/${toolId}`);
    return response.data;
  },
  
  // 切换工具状态
  toggle: async (toolId) => {
    const response = await api.put(`/tools/${toolId}/toggle`);
    return response.data;
  },
  
  // 更新工具配置
  updateConfig: async (toolId, config) => {
    const response = await api.put(`/tools/${toolId}/config`, config);
    return response.data;
  },
  
  // 初始化内置工具
  initBuiltin: async () => {
    const response = await api.post('/tools/builtin/init');
    return response.data;
  },
};

// MCP 相关 API
export const mcpAPI = {
  // 获取 MCP 服务器列表
  listServers: async () => {
    const response = await api.get('/mcp/servers/list');
    return response.data;
  },
  
  // 添加 MCP 服务器
  addServer: async (serverData) => {
    const response = await api.post('/mcp/servers/add', serverData);
    return response.data;
  },
  
  // 删除 MCP 服务器
  deleteServer: async (serverId) => {
    const response = await api.delete(`/mcp/servers/${serverId}`);
    return response.data;
  },
  
  // 测试 MCP 服务器
  testServer: async (serverId) => {
    const response = await api.post(`/mcp/servers/${serverId}/test`);
    return response.data;
  },
  
  // 获取 MCP 工具
  discoverTools: async () => {
    const response = await api.get('/mcp/tools/discover');
    return response.data;
  },
};

// 统一导出
export default {
  // 聊天相关
  sendChatStream: chatAPI.sendChatStream,
  getHistory: chatAPI.getHistory,
  
  // 便捷方法：获取会话历史（使用 chat API）
  getSessionHistory: chatAPI.getHistory,
  
  // 会话相关（便捷方法）
  getSessions: sessionAPI.list,
  createSession: sessionAPI.create,
  deleteSession: sessionAPI.delete,
  // 注意：getSessionHistory 已重定向到 chatAPI.getHistory
  renameSession: sessionAPI.rename,
  exportSession: sessionAPI.export,
  
  // 工具相关（便捷方法）
  getTools: toolAPI.list,
  getTool: toolAPI.get,
  toggleTool: toolAPI.toggle,
  updateToolConfig: toolAPI.updateConfig,
  initBuiltinTools: toolAPI.initBuiltin,
  
  // MCP 相关
  listMCPServers: mcpAPI.listServers,
  addMCPServer: mcpAPI.addServer,
  deleteMCPServer: mcpAPI.deleteServer,
  testMCPServer: mcpAPI.testServer,
  discoverMCPTools: mcpAPI.discoverTools,
};
