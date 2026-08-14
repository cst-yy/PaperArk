import { ExternalLink, Unlink } from "lucide-react";
import { Link } from "react-router-dom";

import type { NoteEvidence } from "./types";

export function EvidenceCard({ evidence, onRemove, removing }: { evidence: NoteEvidence; onRemove: () => void; removing: boolean }) {
  const annotation = evidence.annotation;
  const readerUrl = `/reader/${annotation.paper_id}?document_id=${annotation.document_id}&page=${annotation.page_number}`;
  return <article className="rounded-lg border border-gray-200 p-3 dark:border-slate-700">
    <div className="flex items-center justify-between text-xs text-gray-400"><span>第 {annotation.page_number} 页 · {annotation.type}</span><span>#{evidence.order_index + 1}</span></div>
    <p className="mt-2 line-clamp-5 text-xs leading-5 text-gray-700 dark:text-gray-200">{evidence.quote_snapshot || annotation.selected_text || annotation.comment || "区域标注"}</p>
    <div className="mt-3 flex items-center justify-between">
      <Link to={readerUrl} className="inline-flex items-center gap-1 text-xs text-primary-600"><ExternalLink className="h-3.5 w-3.5" />跳回原文</Link>
      <button type="button" disabled={removing} onClick={onRemove} className="inline-flex items-center gap-1 text-xs text-red-500"><Unlink className="h-3.5 w-3.5" />移除</button>
    </div>
  </article>;
}
