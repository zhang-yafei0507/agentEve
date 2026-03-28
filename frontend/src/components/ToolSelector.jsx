import React, { useState, useMemo } from 'react';
import { Dialog } from '@headlessui/react';
import { useStore } from '../store';

const ToolSelector = ({ isOpen, onClose }) => {
  const { tools, selectedTools, toggleTool, loadTools } = useStore();
  const [searchQuery, setSearchQuery] = useState('');
  const [expandedCategories, setExpandedCategories] = useState(['常用']);

  // 加载工具列表
  React.useEffect(() => {
    if (isOpen && tools.length === 0) {
      loadTools();
    }
  }, [isOpen, tools.length, loadTools]);

  // 按分类分组工具
  const groupedTools = useMemo(() => {
    const groups = {};
    tools.forEach(tool => {
      const category = tool.category || '其他';
      if (!groups[category]) groups[category] = [];
      groups[category].push(tool);
    });
    return groups;
  }, [tools]);

  // 搜索过滤
  const filteredGroups = useMemo(() => {
    if (!searchQuery) return groupedTools;

    const result = {};
    Object.entries(groupedTools).forEach(([category, categoryTools]) => {
      const filtered = categoryTools.filter(tool =>
        tool.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        tool.description.toLowerCase().includes(searchQuery.toLowerCase())
      );
      if (filtered.length > 0) result[category] = filtered;
    });
    return result;
  }, [groupedTools, searchQuery]);

  const toggleCategory = (category) => {
    setExpandedCategories(prev =>
      prev.includes(category)
        ? prev.filter(c => c !== category)
        : [...prev, category]
    );
  };

  const enableAll = () => {
    Object.values(filteredGroups).flat().forEach(tool => {
      if (!selectedTools.includes(tool.id)) toggleTool(tool.id);
    });
  };

  const disableAll = () => {
    Object.values(filteredGroups).flat().forEach(tool => {
      if (selectedTools.includes(tool.id)) toggleTool(tool.id);
    });
  };

  const getCategoryIcon = (category) => {
    const icons = {
      '网络检索': '🔍',
      '数据分析': '📊',
      '编程开发': '💻',
      '文案创作': '✍️',
      'MCP 工具': '🛠️',
      '内置工具': '⚙️',
      '其他': '📦'
    };
    return icons[category] || '📦';
  };

  return (
    <Dialog open={isOpen} onClose={onClose} className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex items-center justify-center min-h-screen px-4">
        <Dialog.Overlay className="fixed inset-0 bg-black opacity-30" />

        <div className="bg-white rounded-lg max-w-4xl w-full max-h-[600px] flex flex-col relative z-10 shadow-xl">
          {/* 标题栏 */}
          <div className="p-6 border-b flex items-center justify-between">
            <Dialog.Title className="text-xl font-bold text-gray-800">
              🛠️ 选择工具
            </Dialog.Title>
            <button 
              onClick={onClose} 
              className="text-gray-400 hover:text-gray-600 transition-colors"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* 搜索框和操作栏 */}
          <div className="p-4 border-b bg-gray-50">
            <div className="flex items-center gap-3">
              <input
                type="text"
                placeholder="搜索工具..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="flex-1 border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <div className="flex gap-2">
                <button
                  onClick={enableAll}
                  className="px-3 py-2 text-sm text-blue-600 hover:bg-blue-50 rounded transition-colors"
                >
                  批量启用
                </button>
                <button
                  onClick={disableAll}
                  className="px-3 py-2 text-sm text-red-600 hover:bg-red-50 rounded transition-colors"
                >
                  批量禁用
                </button>
              </div>
            </div>
            <div className="mt-2 text-xs text-gray-500">
              已选择 {selectedTools.length} / {tools.length} 个工具
            </div>
          </div>

          {/* 工具列表 */}
          <div className="flex-1 overflow-y-auto p-6">
            {Object.keys(filteredGroups).length === 0 ? (
              <div className="text-center py-12 text-gray-500">
                {searchQuery ? '未找到匹配的工具' : '暂无可用工具'}
              </div>
            ) : (
              Object.entries(filteredGroups).map(([category, categoryTools]) => (
                <div key={category} className="mb-6">
                  <button
                    onClick={() => toggleCategory(category)}
                    className="flex items-center justify-between w-full text-left font-medium text-gray-800 mb-3 hover:bg-gray-50 px-3 py-2 rounded transition-colors"
                  >
                    <span className="flex items-center gap-2">
                      <span className="text-xl">{getCategoryIcon(category)}</span>
                      <span>{category}</span>
                      <span className="text-xs text-gray-500 bg-gray-200 px-2 py-0.5 rounded-full">
                        {categoryTools.length}
                      </span>
                    </span>
                    <span className={`transform transition-transform ${
                      expandedCategories.includes(category) ? 'rotate-180' : ''
                    }`}>
                      ▼
                    </span>
                  </button>

                  {expandedCategories.includes(category) && (
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                      {categoryTools.map(tool => (
                        <div
                          key={tool.id}
                          className={`border-2 rounded-lg p-4 cursor-pointer transition-all ${
                            selectedTools.includes(tool.id)
                              ? 'bg-blue-50 border-blue-500 shadow-md'
                              : 'hover:bg-gray-50 hover:border-gray-300 border-gray-200'
                          }`}
                          onClick={() => toggleTool(tool.id)}
                        >
                          <div className="flex items-start justify-between mb-2">
                            <div className="text-2xl">{tool.icon || '🛠️'}</div>
                            <div className={`w-5 h-5 rounded-full border-2 flex items-center justify-center ${
                              selectedTools.includes(tool.id)
                                ? 'bg-blue-500 border-blue-500'
                                : 'border-gray-300'
                            }`}>
                              {selectedTools.includes(tool.id) && (
                                <svg className="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
                                  <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                                </svg>
                              )}
                            </div>
                          </div>
                          
                          <div className="font-medium text-gray-800 truncate mb-1">
                            {tool.name}
                          </div>
                          
                          <div className="text-xs text-gray-500 line-clamp-2 h-8 mb-2">
                            {tool.description || '暂无描述'}
                          </div>
                          
                          <div className="flex items-center justify-between text-xs">
                            <span className={`px-2 py-0.5 rounded ${
                              tool.is_mcp 
                                ? 'bg-purple-100 text-purple-700' 
                                : 'bg-green-100 text-green-700'
                            }`}>
                              {tool.is_mcp ? 'MCP' : '内置'}
                            </span>
                            <span className={`text-xs ${
                              tool.is_enabled ? 'text-green-600' : 'text-gray-400'
                            }`}>
                              {tool.is_enabled ? '已启用' : '已禁用'}
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))
            )}
          </div>

          {/* 底部操作栏 */}
          <div className="p-4 border-t bg-gray-50 flex items-center justify-end gap-3">
            <button
              onClick={onClose}
              className="px-6 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors"
            >
              取消
            </button>
            <button
              onClick={onClose}
              className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors shadow-md"
            >
              确认
            </button>
          </div>
        </div>
      </div>
    </Dialog>
  );
};

export default ToolSelector;
