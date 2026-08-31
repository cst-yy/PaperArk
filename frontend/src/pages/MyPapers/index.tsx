import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Loader2, Search, SlidersHorizontal, X } from "lucide-react";
import clsx from "clsx";
import { PaperCard } from "@/components/PaperCard";
import { RecentReadingList } from "@/features/reading/RecentReadingList";
import { useRecentReading } from "@/features/reading/hooks";
import { useDeletePaper, usePaper, usePapers, useStarPaper, useUnstarPaper } from "@/features/paper/hooks";
import type { PaperListItem, PaperReadingStatus } from "@/features/paper/types";
import { EditPaperDialog } from "@/features/paper/components/EditPaperDialog";
import {
  useMyPaperStats,
  useResearchIdentity,
} from "@/features/research-identity/hooks";

type Authorship = "all" | "first" | "corresponding" | "other";
type SearchPatch = Record<string, string | undefined>;

const ADVANCED_KEYS = [
  "title_query",
  "author_query",
  "abstract_query",
  "venue_query",
  "keyword_query",
  "tag_query",
  "identifier_query",
  "reading_status",
] as const;

export default function MyPapers() {
  const [params, setParams] = useSearchParams();
  const q = params.get("q") ?? "";
  const authorship = (params.get("authorship") ?? "all") as Authorship;
  const yearValue = Number(params.get("year"));
  const year = Number.isInteger(yearValue) && yearValue > 0 ? yearValue : undefined;
  const page = Math.max(1, Number(params.get("page")) || 1);
  const identity = useResearchIdentity();
  const stats = useMyPaperStats();
  const advanced = Object.fromEntries(
    [...ADVANCED_KEYS, "year"].map((key) => [key, params.get(key) ?? undefined]),
  );
  const papers = usePapers({
    mine: true,
    author_role: authorship === "all" ? undefined : authorship,
    year,
    q: q || undefined,
    reading_status: advanced.reading_status as PaperReadingStatus | undefined,
    title_query: advanced.title_query,
    author_query: advanced.author_query,
    abstract_query: advanced.abstract_query,
    venue_query: advanced.venue_query,
    keyword_query: advanced.keyword_query,
    tag_query: advanced.tag_query,
    identifier_query: advanced.identifier_query,
    page,
    page_size: 20,
  });
  const recent = useRecentReading(4, true);
  const [expanded, setExpanded] = useState(false);
  const [editingPaperId, setEditingPaperId] = useState<string | null>(null);
  const editingPaper = usePaper(editingPaperId ?? undefined);
  const starPaper = useStarPaper();
  const unstarPaper = useUnstarPaper();
  const deletePaper = useDeletePaper();
  const years = useMemo(
    () => Array.from({ length: 16 }, (_, index) => new Date().getFullYear() - index),
    [],
  );
  const update = (patch: SearchPatch) => {
    const next = new URLSearchParams(params);
    Object.entries(patch).forEach(([key, value]) => (value ? next.set(key, value) : next.delete(key)));
    if (!("page" in patch)) next.delete("page");
    setParams(next);
  };
  const toggleStar = (paper: PaperListItem) => {
    if (paper.is_starred) unstarPaper.mutate(paper.id);
    else starPaper.mutate(paper.id);
  };

  return (
    <div className="mx-auto w-full max-w-[1500px] space-y-4 p-3 sm:p-4">
      <header className="relative flex min-h-14 items-center gap-3 rounded-xl border border-gray-200 bg-white px-4 py-2 shadow-sm dark:border-slate-700 dark:bg-slate-900">
        <h1 className="shrink-0 text-lg font-semibold">我的论文</h1>
        <MyPaperSearch
          key={q}
          value={q}
          advanced={advanced}
          years={years}
          onSearch={(value) => update({ q: value || undefined })}
          onApply={update}
        />
        <p className="ml-auto hidden shrink-0 text-xs text-gray-500 lg:block">
          {stats.data?.total ?? 0} 篇成果 · 第一/共一 {stats.data?.first_or_co_first ?? 0} · 通讯 {stats.data?.corresponding ?? 0}
        </p>
      </header>

      {!identity.isLoading && !identity.data ? (
        <section className="flex items-center justify-between rounded-lg border border-amber-200 bg-amber-50 px-4 py-2 text-sm text-amber-900 dark:border-amber-900 dark:bg-amber-950/30 dark:text-amber-100">
          <span>尚未设置本人作者身份。</span><Link className="font-medium text-primary-600" to="/settings">前往设置 →</Link>
        </section>
      ) : null}

      <RecentReadingList items={(recent.data ?? []).slice(0, expanded ? 4 : 2)} isLoading={recent.isLoading} expanded={expanded} onToggleExpanded={() => setExpanded((value) => !value)} />

      <section>
        <div className="mb-3 flex flex-wrap items-center gap-2">
          <h2 className="mr-2 text-sm font-semibold">我的成果</h2>
          {([['all', '全部'], ['first', '第一/共一'], ['corresponding', '通讯'], ['other', '其他']] as const).map(([key, label]) => (
            <button key={key} className={clsx("rounded-full px-3 py-1.5 text-xs", authorship === key ? "bg-primary-500 text-white" : "bg-gray-100 text-gray-600 dark:bg-slate-800 dark:text-gray-300")} onClick={() => update({ authorship: key === "all" ? undefined : key })}>{label}</button>
          ))}
          <select aria-label="成果年份" className="input ml-auto h-8 w-28 text-xs" value={year ?? ""} onChange={(event) => update({ year: event.target.value || undefined })}>
            <option value="">全部年份</option>
            {years.map((item) => <option key={item}>{item}</option>)}
          </select>
        </div>
        {papers.isLoading ? (
          <div className="flex min-h-48 items-center justify-center text-sm text-gray-500"><Loader2 className="mr-2 h-4 w-4 animate-spin" />加载成果…</div>
        ) : papers.data?.items.length ? (
          <div className="grid gap-3 md:grid-cols-2">{papers.data.items.map((paper) => <PaperCard key={paper.id} paper={paper} onEdit={setEditingPaperId} onToggleStar={() => toggleStar(paper)} />)}</div>
        ) : (
          <div className="card flex min-h-40 items-center justify-center text-sm text-gray-400">{identity.data ? "当前搜索条件下没有本人署名成果。" : "绑定研究身份后显示本人署名论文。"}</div>
        )}
        {papers.data && papers.data.total_pages > 1 ? (
          <div className="mt-4 flex justify-center gap-2"><button className="btn-ghost" disabled={page <= 1} onClick={() => update({ page: String(page - 1) })}>上一页</button><span className="px-2 py-2 text-xs text-gray-500">{page} / {papers.data.total_pages}</span><button className="btn-ghost" disabled={page >= papers.data.total_pages} onClick={() => update({ page: String(page + 1) })}>下一页</button></div>
        ) : null}
      </section>
      {editingPaperId && editingPaper.data ? <EditPaperDialog paper={editingPaper.data} onClose={() => setEditingPaperId(null)} onDelete={async (paper) => { await deletePaper.mutateAsync(paper.id); setEditingPaperId(null); }} /> : null}
      {editingPaperId && editingPaper.isLoading ? <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/50"><div className="rounded-lg bg-white px-4 py-3 text-sm shadow-lg dark:bg-slate-900"><Loader2 className="mr-2 inline h-4 w-4 animate-spin"/>正在加载论文信息…</div></div> : null}
    </div>
  );
}

function MyPaperSearch({
  value,
  advanced,
  years,
  onSearch,
  onApply,
}: {
  value: string;
  advanced: Record<string, string | undefined>;
  years: number[];
  onSearch: (value: string) => void;
  onApply: (patch: SearchPatch) => void;
}) {
  const [input, setInput] = useState(value);
  const [focused, setFocused] = useState(false);
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const hasAdvanced = ADVANCED_KEYS.some((key) => Boolean(advanced[key]));

  useEffect(() => {
    const timer = setTimeout(() => {
      if (input.trim() !== value) onSearch(input.trim());
    }, 300);
    return () => clearTimeout(timer);
  }, [input, onSearch, value]);

  useEffect(() => {
    const close = (event: PointerEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener("pointerdown", close);
    return () => document.removeEventListener("pointerdown", close);
  }, []);

  return (
    <div ref={rootRef} className={clsx("relative min-w-0 transition-[width] duration-200", focused || open || value ? "w-[min(58vw,46rem)]" : "w-44")}>
      <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
      <input
        type="search"
        aria-label="搜索我的论文"
        className="input h-9 w-full pl-9 pr-11 text-sm"
        placeholder={focused || open ? "搜索标题、作者、摘要、关键词、标签、DOI…" : "搜索论文"}
        value={input}
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
        onChange={(event) => setInput(event.target.value)}
        onKeyDown={(event) => event.key === "Escape" && (setOpen(false), event.currentTarget.blur())}
      />
      <button
        type="button"
        aria-label="高级搜索"
        aria-expanded={open}
        className={clsx("absolute right-1.5 top-1/2 flex h-7 w-7 -translate-y-1/2 items-center justify-center rounded-md", open || hasAdvanced ? "bg-primary-50 text-primary-600 dark:bg-primary-950/40" : "text-gray-400 hover:bg-gray-100 dark:hover:bg-slate-800")}
        onMouseDown={(event) => event.preventDefault()}
        onClick={() => setOpen((current) => !current)}
      >
        <SlidersHorizontal className="h-4 w-4" />
      </button>
      {open ? <AdvancedSearchPanel values={advanced} years={years} onClose={() => setOpen(false)} onApply={(patch) => { onApply(patch); setOpen(false); }} /> : null}
    </div>
  );
}

function AdvancedSearchPanel({ values, years, onClose, onApply }: { values: Record<string, string | undefined>; years: number[]; onClose: () => void; onApply: (patch: SearchPatch) => void }) {
  const [draft, setDraft] = useState<Record<string, string>>(() => Object.fromEntries([...ADVANCED_KEYS, "year"].map((key) => [key, values[key] ?? ""])));
  const field = (key: string, label: string, placeholder: string) => (
    <label className="space-y-1 text-xs text-gray-600 dark:text-gray-300"><span>{label}</span><input className="input h-9 text-sm" value={draft[key] ?? ""} placeholder={placeholder} onChange={(event) => setDraft((current) => ({ ...current, [key]: event.target.value }))} /></label>
  );
  const apply = () => onApply(Object.fromEntries([...ADVANCED_KEYS, "year"].map((key) => [key, draft[key]?.trim() || undefined])));
  const clear = () => {
    const empty = Object.fromEntries([...ADVANCED_KEYS, "year"].map((key) => [key, undefined]));
    setDraft({});
    onApply(empty);
  };

  return (
    <div className="absolute left-0 top-[calc(100%+0.5rem)] z-40 w-[min(820px,calc(100vw-2rem))] rounded-xl border border-gray-200 bg-white p-4 shadow-xl dark:border-slate-700 dark:bg-slate-900">
      <div className="mb-3 flex items-start justify-between gap-3"><div><h2 className="text-sm font-semibold">高级论文搜索</h2><p className="mt-0.5 text-xs text-gray-500">各字段之间按 AND 组合，字段内使用包含匹配；结果保持服务端分页。</p></div><button type="button" className="rounded p-1 text-gray-400 hover:bg-gray-100 dark:hover:bg-slate-800" onClick={onClose}><X className="h-4 w-4" /></button></div>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {field("title_query", "标题", "原文或中文标题")}
        {field("author_query", "作者", "作者姓名")}
        {field("abstract_query", "摘要", "摘要内容")}
        {field("keyword_query", "关键词", "论文关键词")}
        {field("tag_query", "标签", "用户标签")}
        {field("venue_query", "来源", "期刊、会议或出版方")}
        {field("identifier_query", "标识符", "DOI 或 arXiv ID")}
        <label className="space-y-1 text-xs text-gray-600 dark:text-gray-300"><span>年份</span><select className="input h-9 text-sm" value={draft.year ?? ""} onChange={(event) => setDraft((current) => ({ ...current, year: event.target.value }))}><option value="">不限年份</option>{years.map((year) => <option key={year}>{year}</option>)}</select></label>
        <label className="space-y-1 text-xs text-gray-600 dark:text-gray-300"><span>阅读状态</span><select className="input h-9 text-sm" value={draft.reading_status ?? ""} onChange={(event) => setDraft((current) => ({ ...current, reading_status: event.target.value }))}><option value="">不限状态</option><option value="unread">未读</option><option value="reading">阅读中</option><option value="finished">已读</option><option value="archived">已归档</option></select></label>
      </div>
      <div className="mt-4 flex justify-end gap-2"><button type="button" className="btn-ghost" onClick={clear}>清除条件</button><button type="button" className="btn-primary" onClick={apply}>应用搜索</button></div>
    </div>
  );
}
