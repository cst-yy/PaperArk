import { ChevronDown, ChevronRight, ListTree } from "lucide-react";
import { useState } from "react";

import type { OutlineNode } from "../readerTypes";

interface OutlinePanelProps {
  items: OutlineNode[];
  isLoading: boolean;
  activePage: number;
  onJumpToPage: (page: number) => void;
}

export function OutlinePanel({ items, isLoading, activePage, onJumpToPage }: OutlinePanelProps) {
  return (
    <aside className="flex h-full min-h-0 w-64 shrink-0 flex-col border-r border-gray-200 bg-white dark:border-slate-700 dark:bg-slate-900">
      <div className="flex items-center gap-2 border-b border-gray-100 px-4 py-3 text-sm font-medium text-gray-800 dark:border-slate-700 dark:text-gray-100">
        <ListTree className="h-4 w-4" />
        目录
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto p-2">
        {isLoading ? (
          <p className="p-2 text-sm text-gray-400">正在读取目录…</p>
        ) : items.length ? (
          items.map((item) => (
            <OutlineTreeNode
              key={item.id}
              item={item}
              depth={0}
              activePage={activePage}
              onJumpToPage={onJumpToPage}
            />
          ))
        ) : (
          <div className="p-4 text-center text-sm text-gray-400 dark:text-gray-500">暂无可用目录</div>
        )}
      </div>
    </aside>
  );
}

function OutlineTreeNode({
  item,
  depth,
  activePage,
  onJumpToPage,
}: {
  item: OutlineNode;
  depth: number;
  activePage: number;
  onJumpToPage: (page: number) => void;
}) {
  const [expanded, setExpanded] = useState(true);
  const hasChildren = item.children.length > 0;
  const isActive = item.pageNumber === activePage;

  return (
    <div>
      <div
        className={`flex min-w-0 items-center gap-1 rounded-md px-1 py-1 text-sm ${
          isActive
            ? "bg-primary-50 text-primary-700 dark:bg-primary-700/30 dark:text-primary-100"
            : "text-gray-600 hover:bg-gray-50 dark:text-gray-300 dark:hover:bg-slate-800"
        }`}
        style={{ paddingLeft: `${depth * 12 + 4}px` }}
      >
        {hasChildren ? (
          <button
            type="button"
            className="flex h-5 w-5 shrink-0 items-center justify-center rounded hover:bg-black/5 dark:hover:bg-white/10"
            onClick={() => setExpanded((value) => !value)}
            aria-label={expanded ? "收起章节" : "展开章节"}
          >
            {expanded ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
          </button>
        ) : (
          <span className="w-5 shrink-0" />
        )}
        <button
          type="button"
          className="min-w-0 flex-1 truncate text-left"
          disabled={item.pageNumber === null}
          title={item.title}
          onClick={() => item.pageNumber !== null && onJumpToPage(item.pageNumber)}
        >
          {item.title}
        </button>
        {item.pageNumber !== null && <span className="shrink-0 text-xs text-gray-400">{item.pageNumber}</span>}
      </div>
      {hasChildren && expanded && item.children.map((child) => (
        <OutlineTreeNode
          key={child.id}
          item={child}
          depth={depth + 1}
          activePage={activePage}
          onJumpToPage={onJumpToPage}
        />
      ))}
    </div>
  );
}
