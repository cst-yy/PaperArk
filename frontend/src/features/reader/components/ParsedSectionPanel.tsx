import { ListTree } from "lucide-react";
import type { ParsedSection } from "../parsedSections";

interface ParsedSectionPanelProps {
  sections: ParsedSection[];
  isLoading: boolean;
  activePage: number;
  onJumpToPage: (page: number) => void;
}

export function ParsedSectionPanel({ sections, isLoading, activePage, onJumpToPage }: ParsedSectionPanelProps) {
  return (
    <aside className="flex h-full min-h-0 w-64 shrink-0 flex-col border-r border-gray-200 bg-white dark:border-slate-700 dark:bg-slate-900">
      <div className="flex items-center gap-2 border-b border-gray-100 px-4 py-3 text-sm font-medium text-gray-800 dark:border-slate-700 dark:text-gray-100">
        <ListTree className="h-4 w-4" />
        解析结构
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto p-2">
        {isLoading ? <p className="p-2 text-sm text-gray-400">正在读取解析结构…</p> : sections.length ? sections.map((section) => (
          <button
            key={section.id}
            type="button"
            disabled={section.page_start === null}
            onClick={() => section.page_start !== null && onJumpToPage(section.page_start)}
            className={`mb-1 flex w-full items-center gap-2 truncate rounded-md px-2 py-1.5 text-left text-sm hover:bg-gray-50 dark:hover:bg-slate-800 ${section.page_start === activePage ? "bg-primary-50 text-primary-700 dark:bg-primary-700/30 dark:text-primary-100" : "text-gray-600 dark:text-gray-300"}`}
            style={{ paddingLeft: `${8 + Math.min(section.level, 6) * 10}px` }}
            title={section.title}
          >
            <span className="truncate">{section.title}</span>
            {section.page_start !== null && <span className="ml-auto shrink-0 text-xs text-gray-400">{section.page_start}</span>}
          </button>
        )) : <p className="p-4 text-center text-sm text-gray-400 dark:text-gray-500">暂无解析结构</p>}
      </div>
    </aside>
  );
}
