/* ── API 调用 + SSE 流式处理 ── */

import type { SSEEvent, ToolInfo, MCPServerConfig, Session, ChatMessage } from "../types";

const BASE = "http://localhost:8000";

// ─── SSE 流式聊天 ────────────────────────────────
export async function streamChat(
  query: string,
  sessionId: string | null,
  onEvent: (evt: SSEEvent) => void,
  onDone: () => void,
  onError: (err: string) => void
) {
  try {
    const res = await fetch(`${BASE}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, session_id: sessionId }),
    });

    if (!res.ok) {
      onError(`HTTP ${res.status}`);
      return;
    }

    const reader = res.body!.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const parts = buffer.split("\n\n");
      buffer = parts.pop() || "";

      for (const part of parts) {
        for (const line of part.split("\n")) {
          if (line.startsWith("data: ")) {
            try {
              const evt: SSEEvent = JSON.parse(line.slice(6));
              onEvent(evt);
            } catch {
              // skip malformed
            }
          }
        }
      }
    }

    onDone();
  } catch (e: any) {
    onError(e.message || "Network error");
  }
}

// ─── Tools API ───────────────────────────────────
export async function fetchTools(): Promise<ToolInfo[]> {
  const r = await fetch(`${BASE}/api/tools/list`);
  return r.json();
}

export async function configureServer(cfg: MCPServerConfig) {
  const r = await fetch(`${BASE}/api/tools/configure`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(cfg),
  });
  return r.json();
}

export async function toggleTool(toolName: string, enabled: boolean) {
  const r = await fetch(`${BASE}/api/tools/toggle`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ tool_name: toolName, enabled }),
  });
  return r.json();
}

export async function testConnection(cfg: MCPServerConfig) {
  const r = await fetch(`${BASE}/api/tools/test`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(cfg),
  });
  return r.json();
}

export async function removeServer(name: string) {
  const r = await fetch(`${BASE}/api/tools/server/${name}`, { method: "DELETE" });
  return r.json();
}

// ─── Sessions API ────────────────────────────────
export async function fetchSessions(): Promise<Session[]> {
  const r = await fetch(`${BASE}/api/sessions`);
  return r.json();
}

export async function fetchSessionMessages(sessionId: string): Promise<ChatMessage[]> {
  const r = await fetch(`${BASE}/api/sessions/${sessionId}/messages`);
  return r.json();
}
