import { Search as SearchIcon } from "lucide-react";
import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { useSearch } from "@/features/search/hooks";
import { SearchResultCard } from "@/features/search/SearchResultCard";
import type { SearchMode } from "@/features/search/api";

const PAGE_SIZE = 20;

export default function Search() {
  const [params, setParams] = useSearchParams();
  const query = params.get("q")?.trim() ?? "";
  const rawPage = Number(params.get("page"));
  const page = Number.isInteger(rawPage) && rawPage > 0 ? rawPage : 1;
  const requestedMode = params.get("mode");
  const mode: SearchMode = requestedMode === "semantic" || requestedMode === "hybrid" ? requestedMode : "lexical";
  const searchQuery = useSearch(query, page, PAGE_SIZE, mode);
  const updateQuery = (value: string) => {
    const next = new URLSearchParams(params);
    if (value.trim()) next.set("q", value.trim()); else next.delete("q");
    next.delete("page");
    setParams(next, { replace: true });
  };
  const setPage = (nextPage: number) => {
    const next = new URLSearchParams(params);
    if (nextPage <= 1) next.delete("page"); else next.set("page", String(nextPage));
    setParams(next);
  };
  const setMode = (nextMode: SearchMode) => {
    const next = new URLSearchParams(params);
    if (nextMode === "lexical") next.delete("mode"); else next.set("mode", nextMode);
    next.delete("page");
    setParams(next);
  };
  const totalPages = Math.max(1, Math.ceil((searchQuery.data?.total ?? 0) / PAGE_SIZE));

  return <div className="mx-auto max-w-3xl p-6">
    <SearchInput key={query} initialValue={query} onSearch={updateQuery} />
    <div className="mb-4 flex w-fit rounded-lg bg-gray-100 p-1 dark:bg-slate-800"><button className={`rounded-md px-3 py-1.5 text-xs ${mode === "lexical" ? "bg-white font-medium shadow-sm dark:bg-slate-700" : "text-gray-500"}`} onClick={() => setMode("lexical")}>关键词</button><button className={`rounded-md px-3 py-1.5 text-xs ${mode === "semantic" ? "bg-white font-medium shadow-sm dark:bg-slate-700" : "text-gray-500"}`} onClick={() => setMode("semantic")}>语义</button><button className={`rounded-md px-3 py-1.5 text-xs ${mode === "hybrid" ? "bg-white font-medium shadow-sm dark:bg-slate-700" : "text-gray-500"}`} onClick={() => setMode("hybrid")}>混合</button></div>
    {mode === "hybrid" && searchQuery.data?.retrieval?.semantic_available === false && <div className="mb-4 rounded-md bg-amber-50 px-3 py-2 text-xs text-amber-700">语义检索当前不可用，本次结果仅使用关键词检索。</div>}
    {mode === "hybrid" && searchQuery.data?.retrieval?.semantic_available && !searchQuery.data.retrieval.semantic_index_ready && <div className="mb-4 rounded-md bg-blue-50 px-3 py-2 text-xs text-blue-700">当前没有可用语义索引，本次结果仅使用关键词检索。</div>}
    {searchQuery.isFetching ? <div className="py-10 text-center text-sm text-gray-400">正在搜索…</div>
      : searchQuery.isError ? <div className="py-10 text-center text-sm text-red-500">{mode === "semantic" ? "语义检索服务暂不可用，请检查 Embedding 配置。" : "搜索失败，请稍后重试。"}</div>
      : searchQuery.data?.items.length ? <>
        <p className="mb-3 text-xs text-gray-500">共 {searchQuery.data.total} 条研究信息</p>
        <div className="space-y-3">{searchQuery.data.items.map((result) => <SearchResultCard key={`${result.entity_type}-${result.entity_type === "paper" ? result.paper.id : result.note.id}`} result={result} />)}</div>
        {totalPages > 1 && <div className="mt-5 flex items-center justify-center gap-3"><button className="btn-secondary" disabled={page <= 1} onClick={() => setPage(page - 1)}>上一页</button><span className="text-xs text-gray-500">{page} / {totalPages}</span><button className="btn-secondary" disabled={page >= totalPages} onClick={() => setPage(page + 1)}>下一页</button></div>}
      </> : query.length >= 2 ? <div className="py-10 text-center text-sm text-gray-400">{mode === "semantic" ? "暂无可用语义结果，请先生成 Embedding 或尝试其他表达。" : `没有找到与“${query}”相关的论文或笔记`}</div>
        : <div className="py-10 text-center text-sm text-gray-400">输入至少 2 个字符开始搜索</div>}
  </div>;
}

function SearchInput({ initialValue, onSearch }: { initialValue: string; onSearch: (value: string) => void }) {
  const [value, setValue] = useState(initialValue);
  useEffect(() => {
    if (value === initialValue) return;
    const timer = window.setTimeout(() => onSearch(value), 300);
    return () => window.clearTimeout(timer);
  }, [initialValue, onSearch, value]);
  return <div className="relative mb-6"><SearchIcon className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-gray-400" /><input type="text" placeholder="搜索标题、作者、关键词、正文、参考文献和图表…" value={value} onChange={(event) => setValue(event.target.value)} className="input py-3 pl-10 text-base" autoFocus /></div>;
}
