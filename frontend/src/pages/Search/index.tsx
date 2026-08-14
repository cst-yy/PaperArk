import { Search as SearchIcon } from "lucide-react";
import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { useSearch } from "@/features/search/hooks";
import { SearchResultCard } from "@/features/search/SearchResultCard";

const PAGE_SIZE = 20;

export default function Search() {
  const [params, setParams] = useSearchParams();
  const query = params.get("q")?.trim() ?? "";
  const rawPage = Number(params.get("page"));
  const page = Number.isInteger(rawPage) && rawPage > 0 ? rawPage : 1;
  const searchQuery = useSearch(query, page, PAGE_SIZE);
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
  const totalPages = Math.max(1, Math.ceil((searchQuery.data?.total ?? 0) / PAGE_SIZE));

  return <div className="mx-auto max-w-3xl p-6">
    <SearchInput key={query} initialValue={query} onSearch={updateQuery} />
    {searchQuery.isFetching ? <div className="py-10 text-center text-sm text-gray-400">正在搜索…</div>
      : searchQuery.isError ? <div className="py-10 text-center text-sm text-red-500">搜索失败，请稍后重试。</div>
      : searchQuery.data?.items.length ? <>
        <p className="mb-3 text-xs text-gray-500">共 {searchQuery.data.total} 条研究信息</p>
        <div className="space-y-3">{searchQuery.data.items.map((result) => <SearchResultCard key={`${result.entity_type}-${result.entity_type === "paper" ? result.paper.id : result.note.id}`} result={result} />)}</div>
        {totalPages > 1 && <div className="mt-5 flex items-center justify-center gap-3"><button className="btn-secondary" disabled={page <= 1} onClick={() => setPage(page - 1)}>上一页</button><span className="text-xs text-gray-500">{page} / {totalPages}</span><button className="btn-secondary" disabled={page >= totalPages} onClick={() => setPage(page + 1)}>下一页</button></div>}
      </> : query.length >= 2 ? <div className="py-10 text-center text-sm text-gray-400">没有找到与“{query}”相关的论文或笔记</div>
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
