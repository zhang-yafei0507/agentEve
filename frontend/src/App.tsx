import React from "react";
import { BrowserRouter, Routes, Route, Link } from "react-router-dom";
import ChatPage from "./pages/ChatPage";
import ToolManager from "./pages/ToolManager";

const App: React.FC = () => (
  <BrowserRouter>
    <div className="h-screen flex flex-col">
      {/* ── Top Nav ── */}
      <nav className="h-10 flex items-center gap-6 px-5 bg-gray-50 dark:bg-gray-900 border-b dark:border-gray-800 text-sm">
        <span className="font-bold text-blue-600">AgentRAG</span>
        <Link to="/" className="hover:text-blue-600">Chat</Link>
        <Link to="/tools" className="hover:text-blue-600">Tools</Link>
      </nav>

      {/* ── Pages ── */}
      <div className="flex-1 overflow-hidden">
        <Routes>
          <Route path="/" element={<ChatPage />} />
          <Route path="/tools" element={<ToolManager />} />
        </Routes>
      </div>
    </div>
  </BrowserRouter>
);

export default App;
