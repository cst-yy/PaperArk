import { FileText } from "lucide-react";
import { Link } from "react-router-dom";

import type { SearchMatch, SearchPaperResult, SearchSource } from "./types";

const SOURCE_LABELS: Record<SearchSource, string> = {
  title: "Title", abstract: "Abstract", author: "Author", tag: "Tag", keyword: "Keyword",
  doi: "DOI", arxiv: "arXiv", journal: "Journal", conference: "Conference",
  publisher: "Publisher", section: "Section", chunk: "Full Text", reference: "Reference",
  figure: "Figure", table: "Table",
};

function readerTarget(paperId: string, match: SearchMatch): string {
  const params = new URLSearchParams();
  if (match.document_id) params.set("document_id", match.document_id);
  if (match.page_start) params.set("page", String(match.page_start));
  const query = params.toString();
  return `/reader/${paperId}${query ? `?${query}` : ""}`;
}

export function SearchResultCard({ result }: { result: SearchPaperResult }) {
  const primary = result.matches[0];
  return <article className="card transition-shadow hover:shadow-md">
    <Link to={primary ? readerTarget(result.paper.id, primary) : `/reader/${result.paper.id}`} className="flex items-start gap-3">
      <FileText className="mt-0.5 h-4 w-4 shrink-0 text-gray-400" />
      <div className="min-w-0 flex-1">
        <h2 className="text-sm font-medium text-gray-900 dark:text-gray-100">{result.paper.title}</h2>
        <p className="mt-1 text-xs text-gray-500">{result.paper.authors.slice(0, 3).join(", ") || "未知作者"}{result.paper.publication_year ? ` · ${result.paper.publication_year}` : ""}</p>
      </div>
      <span className="shrink-0 text-[11px] text-gray-400">命中 {result.match_count} 处</span>
    </Link>
    <div className="mt-3 space-y-2">
      {result.matches.slice(0, 3).map((match, index) => <Link key={`${match.source}-${index}-${match.section_id ?? ""}`} to={readerTarget(result.paper.id, match)} className="block rounded-md bg-gray-50 px-3 py-2 hover:bg-gray-100 dark:bg-slate-800 dark:hover:bg-slate-700">
        <div className="mb-1 flex items-center gap-2"><span className="rounded bg-white px-1.5 py-0.5 text-[10px] font-medium text-primary-700 dark:bg-slate-900 dark:text-primary-200">{SOURCE_LABELS[match.source]}</span>{match.page_start && <span className="text-[10px] text-gray-400">P{match.page_start}</span>}</div>
        <p className="line-clamp-2 text-xs leading-5 text-gray-600 dark:text-gray-300">{match.snippet || match.text}</p>
      </Link>)}
    </div>
  </article>;
}
