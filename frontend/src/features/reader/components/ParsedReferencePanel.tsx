import { BookMarked, ExternalLink } from "lucide-react";
import type { ParsedReference } from "../parsedReferences";

interface ParsedReferencePanelProps {
  references: ParsedReference[];
  isLoading: boolean;
  onJumpToPage: (page: number) => void;
  onOpenPaper: (paperId: string) => void;
}

export function ParsedReferencePanel({ references, isLoading, onJumpToPage, onOpenPaper }: ParsedReferencePanelProps) {
  return <aside className="flex h-full min-h-0 w-64 shrink-0 flex-col border-r border-gray-200 bg-white dark:border-slate-700 dark:bg-slate-900">
    <div className="flex items-center gap-2 border-b border-gray-100 px-4 py-3 text-sm font-medium text-gray-800 dark:border-slate-700 dark:text-gray-100"><BookMarked className="h-4 w-4" />参考文献{references.length ? ` (${references.length})` : ""}</div>
    <div data-reference-scroll className="min-h-0 flex-1 overflow-y-auto p-2">
      {isLoading ? <p className="p-2 text-sm text-gray-400">正在读取参考文献…</p> : references.length ? references.map((reference) => <div key={reference.id} className="mb-2 rounded-md border border-gray-100 p-2 text-left text-xs dark:border-slate-800">
        <button type="button" onClick={() => onJumpToPage(reference.page_start)} className="w-full text-left leading-5 text-gray-600 hover:text-primary-700 dark:text-gray-300 dark:hover:text-primary-200" title="定位到 PDF 页面"><span className="mr-1 font-medium text-gray-900 dark:text-gray-100">[{reference.order_index + 1}]</span>{reference.title ?? reference.raw_text}</button>
        {reference.matched_paper ? <button type="button" onClick={() => onOpenPaper(reference.matched_paper!.id)} className="mt-1 inline-flex items-center gap-1 text-xs text-primary-700 hover:underline dark:text-primary-200"><ExternalLink className="h-3 w-3" />已在论文库</button> : <p className="mt-1 text-xs text-gray-400">未收藏</p>}
      </div>) : <p className="p-4 text-center text-sm text-gray-400 dark:text-gray-500">暂无参考文献</p>}
    </div>
  </aside>;
}
