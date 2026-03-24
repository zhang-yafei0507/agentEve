import React, { useState, useRef, useEffect, useCallback } from "react";
import { streamChat, fetchSessions, fetchSessionMessages } from "../api/api";
import ChatMessage from "../components/ChatMessage";
import AgentVisualizer from "../components/AgentVisualizer";
import type { ChatMessage as Msg, SSEEvent, VisualizationState, Session } from "../types";

const INIT_VIS: VisualizationState = {
  agents: {},
  sharedBoard: {},
  toolCalls: [],
  plan: null,
};

const ChatPage: React.FC = () => {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [vis, setVis] = useState<VisualizationState>({ ...INIT_VIS });
  const bottomRef = useRef<HTMLDivElement>(null);

  // 加载 sessions
  useEffect(() => {
    fetchSessions().then(setSessions).catch(() => {});
  }, []);

  // 切换 session 时加载历史
  const selectSession = useCallback(async (id: string) => {
    setSessionId(id);
    const msgs = await fetchSessionMessages(id);
    setMessages(msgs);
    setVis({ ...INIT_VIS });
  }, []);

  // 自动滚底
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // 处理 SSE 事件
  const handleEvent = useCallback((evt: SSEEvent) => {
    switch (evt.type) {
      case "session":
        setSessionId(evt.session_id);
        break;

      case "thinking":
        setVis((v) => ({
          ...v,
          agents: {
            ...v.agents,
            [evt.agent]: {
              ...v.agents[evt.agent],
              name: evt.agent,
              status: "working",
              thinking: evt.content,
            },
          },
        }));
        break;

      case "plan":
        setVis((v) => ({ ...v, plan: evt.plan }));
        break;

      case "agent_start":
        setVis((v) => ({
          ...v,
          agents: {
            ...v.agents,
            [evt.agent]: { name: evt.agent, status: "working", task: evt.task },
          },
        }));
        break;

      case "tool_call":
        setVis((v) => ({
          ...v,
          agents: {
            ...v.agents,
            [evt.agent]: {
              ...v.agents[evt.agent],
              currentTool: { tool: evt.tool, args: evt.args },
            },
          },
          toolCalls: [...v.toolCalls, { agent: evt.agent, tool: evt.tool, args: evt.args }],
        }));
        break;

      case "tool_result":
        setVis((v) => {
          const updated = v.toolCalls.map((tc, i) =>
            i === v.toolCalls.length - 1 ? { ...tc, result: evt.result } : tc
          );
          return {
            ...v,
            toolCalls: updated,
            agents: {
              ...v.agents,
              [evt.agent]: { ...v.agents[evt.agent], currentTool: undefined },
            },
          };
        });
        break;

      case "shared_state_update":
        setVis((v) => ({
          ...v,
          sharedBoard: { ...v.sharedBoard, [evt.key]: evt.value },
        }));
        break;

      case "agent_complete":
        setVis((v) => ({
          ...v,
          agents: {
            ...v.agents,
            [evt.agent]: {
              ...v.agents[evt.agent],
              status: "done",
              output: evt.output,
              currentTool: undefined,
            },
          },
        }));
        break;

      case "response":
        // 合成结果流式追加到末尾 assistant 消息
        setMessages((prev) => {
          const last = prev[prev.length - 1];
          if (last && last.role === "assistant") {
            return [...prev.slice(0, -1), { ...last, content: evt.content }];
          }
          return [...prev, { role: "assistant", content: evt.content }];
        });
        break;

      case "done":
        setMessages((prev) => {
          const last = prev[prev.length - 1];
          if (last && last.role === "assistant") {
            return [...prev.slice(0, -1), { ...last, content: evt.content }];
          }
          return [...prev, { role: "assistant", content: evt.content }];
        });
        break;

      case "error":
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: `⚠️ Error: ${evt.content}` },
        ]);
        break;
    }
  }, []);

  // 发送消息
  const send = async () => {
    const q = input.trim();
    if (!q || streaming) return;
    setInput("");
    setStreaming(true);
    setVis({ ...INIT_VIS });
    setMessages((prev) => [...prev, { role: "user", content: q }]);

    await streamChat(
      q,
      sessionId,
      handleEvent,
      () => {
        setStreaming(false);
        fetchSessions().then(setSessions).catch(() => {});
      },
      (err) => {
        setMessages((prev) => [...prev, { role: "assistant", content: `⚠️ ${err}` }]);
        setStreaming(false);
      }
    );
  };

  return (
    <div className="flex h-screen bg-white dark:bg-gray-950 text-gray-900 dark:text-gray-100">
      {/* ── Left: Session List ── */}
      <aside className="w-56 border-r dark:border-gray-800 flex flex-col">
        <div className="p-3 border-b dark:border-gray-800">
          <button
            onClick={() => { setSessionId(null); setMessages([]); setVis({ ...INIT_VIS }); }}
            className="w-full py-2 rounded-lg bg-blue-600 text-white text-sm hover:bg-blue-700"
          >
            + New Chat
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {sessions.map((s) => (
            <button
              key={s.id}
              onClick={() => selectSession(s.id)}
              className={`w-full text-left px-3 py-2 rounded-lg text-sm truncate ${
                sessionId === s.id ? "bg-blue-50 dark:bg-gray-800 font-medium" : "hover:bg-gray-100 dark:hover:bg-gray-800"
              }`}
            >
              {s.title}
            </button>
          ))}
        </div>
      </aside>

      {/* ── Center: Chat ── */}
      <main className="flex-1 flex flex-col min-w-0">
        <header className="h-12 flex items-center px-4 border-b dark:border-gray-800 text-sm font-medium">
          Agentic RAG Chat
          {streaming && <span className="ml-2 text-xs text-yellow-500 animate-pulse">● streaming</span>}
        </header>

        <div className="flex-1 overflow-y-auto px-4 py-6">
          {messages.map((m, i) => (
            <ChatMessage key={i} message={m} />
          ))}
          <div ref={bottomRef} />
        </div>

        <div className="p-4 border-t dark:border-gray-800">
          <div className="flex gap-2">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && send()}
              placeholder="Ask anything…"
              className="flex-1 px-4 py-2.5 rounded-xl border dark:border-gray-700 bg-gray-50 dark:bg-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
              disabled={streaming}
            />
            <button
              onClick={send}
              disabled={streaming || !input.trim()}
              className="px-5 py-2.5 rounded-xl bg-blue-600 text-white text-sm font-medium disabled:opacity-40 hover:bg-blue-700"
            >
              Send
            </button>
          </div>
        </div>
      </main>

      {/* ── Right: Visualizer Panel ── */}
      <aside className="w-96 border-l dark:border-gray-800 flex flex-col">
        <header className="h-12 flex items-center px-4 border-b dark:border-gray-800 text-sm font-medium">
          Agent Collaboration Panel
        </header>
        <AgentVisualizer vis={vis} />
      </aside>
    </div>
  );
};

export default ChatPage;
