import React from "react";
import type { ToolInfo } from "../types";

interface Props {
  tool: ToolInfo;
  onToggle: (name: string, enabled: boolean) => void;
}

const ToolCard: React.FC<Props> = ({ tool, onToggle }) => (
  <tr className="border-b dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800">
    <td className="px-4 py-3 font-mono text-sm">{tool.name}</td>
    <td className="px-4 py-3">
      <span
        className={`text-xs px-2 py-0.5 rounded-full ${
          tool.source === "mcp"
            ? "bg-purple-100 text-purple-700 dark:bg-purple-900 dark:text-purple-300"
            : "bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300"
        }`}
      >
        {tool.source.toUpperCase()}
      </span>
    </td>
    <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-400 max-w-xs truncate">
      {tool.description}
    </td>
    <td className="px-4 py-3 text-xs text-gray-500">{tool.server_name}</td>
    <td className="px-4 py-3">
      <button
        onClick={() => onToggle(tool.name, !tool.enabled)}
        className={`relative inline-flex h-6 w-11 items-center rounded-full transition ${
          tool.enabled ? "bg-green-500" : "bg-gray-300 dark:bg-gray-600"
        }`}
      >
        <span
          className={`inline-block h-4 w-4 rounded-full bg-white transform transition ${
            tool.enabled ? "translate-x-6" : "translate-x-1"
          }`}
        />
      </button>
    </td>
  </tr>
);

export default ToolCard;
