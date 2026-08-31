import { BarChart2, Table2 } from "lucide-react";
import type { ParsedElement } from "../parsedElements";

interface ParsedElementPanelProps {
  elements: ParsedElement[];
  isLoading: boolean;
  onJumpToPage: (page: number) => void;
}

export function ParsedElementPanel({ elements, isLoading, onJumpToPage }: ParsedElementPanelProps) {
  const figures = elements.filter((element) => element.element_type === "figure");
  const tables = elements.filter((element) => element.element_type === "table");
  return <aside className="flex h-full min-h-0 w-64 shrink-0 flex-col border-r border-gray-200 bg-white dark:border-slate-700 dark:bg-slate-900">
    <div className="border-b border-gray-100 px-4 py-3 text-sm font-medium text-gray-800 dark:border-slate-700 dark:text-gray-100">文档元素</div>
    <div className="min-h-0 flex-1 overflow-y-auto p-2">
      {isLoading ? <p className="p-2 text-sm text-gray-400">正在读取文档元素…</p> : elements.length ? <>
        <ElementGroup title={`Figures (${figures.length})`} icon={<BarChart2 className="h-3.5 w-3.5" />} elements={figures} onJumpToPage={onJumpToPage} />
        <ElementGroup title={`Tables (${tables.length})`} icon={<Table2 className="h-3.5 w-3.5" />} elements={tables} onJumpToPage={onJumpToPage} />
      </> : <p className="p-4 text-center text-sm text-gray-400 dark:text-gray-500">暂无图表元素</p>}
    </div>
  </aside>;
}

function ElementGroup({ title, icon, elements, onJumpToPage }: { title: string; icon: React.ReactNode; elements: ParsedElement[]; onJumpToPage: (page: number) => void }) {
  if (!elements.length) return null;
  return <section className="mb-3"><div className="flex items-center gap-1.5 px-2 py-1 text-xs font-medium text-gray-500 dark:text-gray-400">{icon}{title}</div>{elements.map((element) => <button key={element.id} type="button" onClick={() => onJumpToPage(element.page_number)} className="mb-1 w-full rounded-md px-2 py-1.5 text-left text-xs text-gray-600 hover:bg-gray-50 dark:text-gray-300 dark:hover:bg-slate-800" title={element.caption}><span className="block truncate font-medium text-gray-800 dark:text-gray-100">{element.label ?? element.element_type}</span><span className="block truncate text-gray-400">{element.caption}</span></button>)}</section>;
}
