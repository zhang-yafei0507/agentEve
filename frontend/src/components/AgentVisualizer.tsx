import React from "react";
import type { VisualizationState, ToolCallLog } from "../types";

interface Props {
  vis: VisualizationState;
}

const statusColor: Record<string, string> = {
  idle: "bg-gray-300 dark:bg-gray-600",
  working: "bg-yellow-400 animate-pulse",
  done: "bg-green-500",
  error: "bg-red-500",
};

const AgentVisualizer: React.FC<Props> = ({ vis }) => {
  const agents = Object.values(vis.agents);

  return (
    <div className="h-full overflow-y-auto p-4 space-y-5 text-sm">
      {/* ── Plan ── */}
      {vis.plan && (
        <section>
          <h3 className="font-semibold text-xs uppercase tracking-wider text-gray-500 mb-2">
            Execution Plan
          </h3>
          <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-3 text-xs">
            <pre className="whitespace-pre-wrap">{JSON.stringify(vis.plan, null, 2)}</pre>
          </div>
        </section>
      )}

      {/* ── Agent Nodes ── */}
      <section>
        <h3 className="font-semibold text-xs uppercase tracking-wider text-gray-500 mb-2">
          Agents
        </h3>
        <div className="grid grid-cols-2 gap-3">
          {agents.map((a) => (
            <div
              key={a.name}
              className="border dark:border-gray-700 rounded-xl p-3 space-y-1 bg-white dark:bg-gray-900"
            >
              <div className="flex items-center gap-2">
                <span className={`w-2.5 h-2.5 rounded-full ${statusColor[a.status]}`} />
                <span className="font-medium capitalize">{a.name}</span>
              </div>
              {a.task && <p className="text-xs text-gray-500 line-clamp-2">{a.task}</p>}
              {a.currentTool && (
                <p className="text-xs text-blue-500">
                  🔧 {a.currentTool.tool}
                </p>
              )}
              {a.status === "done" && a.output && (
                <details className="text-xs">
                  <summary className="cursor-pointer text-green-600">View output</summary>
                  <p className="mt-1 bg-gray-50 dark:bg-gray-800 p-2 rounded max-h-40 overflow-y-auto whitespace-pre-wrap">
                    {a.output}
                  </p>
                </details>
              )}
            </div>
          ))}
        </div>
      </section>

      {/* ── Shared Board ── */}
      <section>
        <h3 className="font-semibold text-xs uppercase tracking-wider text-gray-500 mb-2">
          Shared State Board
        </h3>
        {Object.keys(vis.sharedBoard).length === 0 ? (
          <p className="text-xs text-gray-400 italic">Empty</p>
        ) : (
          <div className="space-y-2">
            {Object.entries(vis.sharedBoard).map(([k, v]) => (
              <details key={k} className="text-xs border dark:border-gray-700 rounded-lg">
                <summary className="px-3 py-2 cursor-pointer font-medium">{k}</summary>
                <div className="px-3 pb-2 max-h-32 overflow-y-auto whitespace-pre-wrap text-gray-600 dark:text-gray-400">
                  {v}
                </div>
              </details>
            ))}
          </div>
        )}
      </section>

      {/* ── Tool Calls ── */}
      {vis.toolCalls.length > 0 && (
        <section>
          <h3 className="font-semibold text-xs uppercase tracking-wider text-gray-500 mb-2">
            Tool Calls ({vis.toolCalls.length})
          </h3>
          <div className="space-y-1 max-h-48 overflow-y-auto">
            {vis.toolCalls.map((tc, i) => (
              <div
                key={i}
                className="text-xs bg-gray-50 dark:bg-gray-800 rounded px-3 py-1.5 flex items-center gap-2"
              >
                <span className="font-medium text-blue-600">{tc.agent}</span>
                <span>→</span>
                <span className="font-mono">{tc.tool}</span>
                {tc.result && <span className="text-green-600 ml-auto">✓</span>}
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
};

export default AgentVisualizer;
