import React, { useEffect, useState } from "react";
import { fetchTools, configureServer, toggleTool, testConnection, removeServer } from "../api/api";
import ToolCard from "../components/ToolCard";
import type { ToolInfo, MCPServerConfig } from "../types";

const emptyConfig: MCPServerConfig = {
  name: "",
  transport: "stdio",
  command: "",
  args: [],
  env_vars: {},
};

const ToolManager: React.FC = () => {
  const [tools, setTools] = useState<ToolInfo[]>([]);
  const [form, setForm] = useState<MCPServerConfig>({ ...emptyConfig });
  const [argsStr, setArgsStr] = useState("");
  const [testResult, setTestResult] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const load = () => fetchTools().then(setTools).catch(() => {});
  useEffect(() => { load(); }, []);

  const handleToggle = async (name: string, enabled: boolean) => {
    await toggleTool(name, enabled);
    load();
  };

  const handleAdd = async () => {
    if (!form.name) return;
    setLoading(true);
    try {
      const cfg = { ...form, args: argsStr.split(/\s+/).filter(Boolean) };
      await configureServer(cfg);
      setForm({ ...emptyConfig });
      setArgsStr("");
      load();
    } catch (e: any) {
      alert(e.message);
    }
    setLoading(false);
  };

  const handleTest = async () => {
    setTestResult("Testing…");
    const cfg = { ...form, args: argsStr.split(/\s+/).filter(Boolean) };
    const res = await testConnection(cfg);
    setTestResult(res.success ? `✅ Connected — ${res.tool_count} tools` : `❌ ${res.error}`);
  };

  // 聚合 servers
  const servers = [...new Set(tools.filter((t) => t.source === "mcp").map((t) => t.server_name))];

  return (
    <div className="min-h-screen bg-white dark:bg-gray-950 text-gray-900 dark:text-gray-100">
      <div className="max-w-6xl mx-auto p-6 space-y-8">
        <h1 className="text-2xl font-bold">MCP Tool Manager</h1>

        {/* ── Add Server Form ── */}
        <section className="border dark:border-gray-800 rounded-xl p-5 space-y-4">
          <h2 className="font-semibold">Add MCP Server</h2>
          <div className="grid grid-cols-2 gap-4">
            <input
              placeholder="Server name"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              className="px-3 py-2 rounded-lg border dark:border-gray-700 bg-gray-50 dark:bg-gray-900 text-sm"
            />
            <select
              value={form.transport}
              onChange={(e) => setForm({ ...form, transport: e.target.value as any })}
              className="px-3 py-2 rounded-lg border dark:border-gray-700 bg-gray-50 dark:bg-gray-900 text-sm"
            >
              <option value="stdio">stdio</option>
              <option value="sse">SSE</option>
            </select>
            {form.transport === "stdio" ? (
              <>
                <input
                  placeholder="Command (e.g. npx)"
                  value={form.command || ""}
                  onChange={(e) => setForm({ ...form, command: e.target.value })}
                  className="px-3 py-2 rounded-lg border dark:border-gray-700 bg-gray-50 dark:bg-gray-900 text-sm"
                />
                <input
                  placeholder="Args (space-separated, e.g. -y mcp-server-fetch)"
                  value={argsStr}
                  onChange={(e) => setArgsStr(e.target.value)}
                  className="px-3 py-2 rounded-lg border dark:border-gray-700 bg-gray-50 dark:bg-gray-900 text-sm"
                />
              </>
            ) : (
              <input
                placeholder="SSE URL"
                value={form.url || ""}
                onChange={(e) => setForm({ ...form, url: e.target.value })}
                className="col-span-2 px-3 py-2 rounded-lg border dark:border-gray-700 bg-gray-50 dark:bg-gray-900 text-sm"
              />
            )}
          </div>
          <div className="flex gap-3">
            <button onClick={handleTest} className="px-4 py-2 rounded-lg bg-gray-200 dark:bg-gray-800 text-sm hover:bg-gray-300">
              Test Connection
            </button>
            <button
              onClick={handleAdd}
              disabled={loading || !form.name}
              className="px-4 py-2 rounded-lg bg-blue-600 text-white text-sm disabled:opacity-40 hover:bg-blue-700"
            >
              {loading ? "Connecting…" : "Add Server"}
            </button>
          </div>
          {testResult && <p className="text-sm">{testResult}</p>}
        </section>

        {/* ── Connected Servers ── */}
        {servers.length > 0 && (
          <section className="space-y-2">
            <h2 className="font-semibold">Connected Servers</h2>
            <div className="flex flex-wrap gap-2">
              {servers.map((s) => (
                <span
                  key={s}
                  className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs bg-purple-100 dark:bg-purple-900 text-purple-700 dark:text-purple-300"
                >
                  {s}
                  <button
                    onClick={async () => { await removeServer(s); load(); }}
                    className="hover:text-red-500"
                  >
                    ✕
                  </button>
                </span>
              ))}
            </div>
          </section>
        )}

        {/* ── Tool Table ── */}
        <section>
          <h2 className="font-semibold mb-3">Tools ({tools.length})</h2>
          <div className="border dark:border-gray-800 rounded-xl overflow-hidden">
            <table className="w-full">
              <thead className="bg-gray-50 dark:bg-gray-900 text-xs uppercase text-gray-500">
                <tr>
                  <th className="px-4 py-3 text-left">Name</th>
                  <th className="px-4 py-3 text-left">Source</th>
                  <th className="px-4 py-3 text-left">Description</th>
                  <th className="px-4 py-3 text-left">Server</th>
                  <th className="px-4 py-3 text-left">Enabled</th>
                </tr>
              </thead>
              <tbody>
                {tools.map((t) => (
                  <ToolCard key={t.name} tool={t} onToggle={handleToggle} />
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </div>
  );
};

export default ToolManager;
