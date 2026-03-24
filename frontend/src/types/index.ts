/* ── 全局类型定义 ── */

export interface ChatMessage {
  role: "user" | "assistant" | "system";
  content: string;
  created_at?: string;
}

export interface SSEEvent {
  type:
    | "session"
    | "thinking"
    | "plan"
    | "agent_start"
    | "tool_call"
    | "tool_result"
    | "shared_state_update"
    | "agent_complete"
    | "response"
    | "error"
    | "done";
  [key: string]: any;
}

export interface AgentNode {
  name: string;
  status: "idle" | "working" | "done" | "error";
  task?: string;
  output?: string;
  thinking?: string;
  currentTool?: { tool: string; args: Record<string, any> };
}

export interface ToolCallLog {
  agent: string;
  tool: string;
  args: Record<string, any>;
  result?: string;
}

export interface VisualizationState {
  agents: Record<string, AgentNode>;
  sharedBoard: Record<string, string>;
  toolCalls: ToolCallLog[];
  plan: any | null;
}

export interface ToolInfo {
  name: string;
  description: string;
  source: "mcp" | "local";
  server_name: string;
  enabled: boolean;
}

export interface MCPServerConfig {
  name: string;
  transport: "stdio" | "sse";
  command?: string;
  args: string[];
  env_vars: Record<string, string>;
  url?: string;
}

export interface Session {
  id: string;
  title: string;
  created_at: string;
}
