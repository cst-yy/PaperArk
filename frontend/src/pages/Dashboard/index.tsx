import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { BookCheck, BookOpen, Clock3, FileText, Loader2, Search, Upload } from "lucide-react";

import { ImportModal } from "@/components/ImportModal";
import { ReadingTrendChart, type TrendMetric } from "@/features/dashboard/components/ReadingTrendChart";
import { TopicCloud } from "@/features/dashboard/components/TopicCloud";
import { useDashboard, useReadingTrend } from "@/features/dashboard/hooks";
import { DashboardSplitSlot } from "@/features/dashboard/DashboardSplitSlot";
import { TodoWidget } from "@/features/dashboard/TodoWidget";
import { MemoWidget } from "@/features/dashboard/MemoWidget";

const STATUS_LABELS: Record<string, string> = { unread: "未读", reading: "阅读中", finished: "已读", archived: "已归档" };
const NOTE_LABELS: Record<string, string> = { general: "普通", paper: "论文", research: "研究" };

function formatTime(value: string | null) {
  if (!value) return "尚未备份";
  return new Intl.DateTimeFormat("zh-CN", { month: "numeric", day: "numeric", hour: "2-digit", minute: "2-digit" }).format(new Date(value));
}

export default function Dashboard() {
  const navigate = useNavigate();
  const [showImportModal, setShowImportModal] = useState(false);
  const [trendDays, setTrendDays] = useState<7 | 30 | 90>(7);
  const [showAllReading, setShowAllReading] = useState(false);
  const [searchText, setSearchText] = useState("");
  const [trendMetric, setTrendMetric] = useState<TrendMetric>("papers");
  const [topicType, setTopicType] = useState<"tag" | "keyword">("tag");
  const [topicDays, setTopicDays] = useState<7 | 30>(30);
  const [topicLimit, setTopicLimit] = useState<20 | 50>(20);
  const dashboard = useDashboard(topicDays, topicLimit);
  const trend = useReadingTrend(trendDays);

  if (dashboard.isLoading) return <div className="flex min-h-[420px] items-center justify-center text-sm text-gray-500"><Loader2 className="mr-2 h-4 w-4 animate-spin" />正在加载研究概览…</div>;
  if (dashboard.isError || !dashboard.data) return <div className="mx-auto mt-16 max-w-lg rounded-xl border border-red-200 bg-red-50 p-6 text-center"><p className="font-medium text-red-700">仪表盘暂时无法加载</p><button className="btn-ghost mt-3" onClick={() => void dashboard.refetch()}>重新加载</button></div>;

  const data = dashboard.data;
  const overview = [
    { label: "论文总数", value: data.overview.total_papers, icon: BookOpen, color: "text-blue-500", href: "/library" },
    { label: "阅读中", value: data.overview.reading_papers, icon: Clock3, color: "text-amber-500", href: "/library?reading_status=reading" },
    { label: "已读", value: data.overview.finished_papers, icon: BookCheck, color: "text-emerald-500", href: "/library?reading_status=finished" },
    { label: "研究笔记", value: data.overview.research_notes, icon: FileText, color: "text-violet-500", href: "/notes" },
  ];

  return <div className="mx-auto w-full max-w-[1500px] space-y-3 p-3 sm:p-4 xl:flex xl:h-full xl:min-h-0 xl:flex-col xl:gap-3 xl:space-y-0 xl:[&>div:nth-of-type(2)]:min-h-[238px] xl:[&>div:nth-of-type(2)]:flex-1 xl:[&>div:nth-of-type(2)>section:first-child]:flex xl:[&>div:nth-of-type(2)>section:first-child]:flex-col">
    <nav aria-label="研究进展导航" className="relative z-20 flex min-h-14 shrink-0 items-center gap-2 rounded-xl border border-gray-200 bg-white px-3 py-2 shadow-sm dark:border-slate-700 dark:bg-slate-900">
      <h1 className="mr-1 shrink-0 text-lg font-semibold tracking-tight">研究进展</h1>
      <form className="relative shrink-0" onSubmit={(event) => { event.preventDefault(); const query = searchText.trim(); if (query) navigate(`/search?q=${encodeURIComponent(query)}`); }}><Search className="pointer-events-none absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" /><input className="input w-36 py-1.5 pl-8 text-xs focus:w-64" type="search" value={searchText} onChange={(event) => setSearchText(event.target.value)} placeholder="搜索" aria-label="搜索论文、笔记和 PDF 正文" /></form>
      <div className="ml-auto hidden min-w-0 flex-1 items-center justify-end gap-1 lg:flex">{overview.map((item) => <Link key={item.label} to={item.href} className="flex min-w-24 items-center justify-center gap-1.5 rounded-lg px-2 py-1.5 transition-colors hover:bg-gray-50 dark:hover:bg-slate-800"><item.icon className={`h-4 w-4 ${item.color}`} /><strong className="text-sm">{item.value}</strong><span className="text-[11px] text-gray-500">{item.label}</span></Link>)}</div>
      <Link to="/settings" className="hidden shrink-0 text-[11px] text-gray-500 hover:text-primary-600 xl:block">备份 {formatTime(data.backup.last_backup_at)}</Link><button className="btn-primary shrink-0 px-3 py-1.5 text-xs" onClick={() => setShowImportModal(true)}><Upload className="h-3.5 w-3.5" />导入</button>
    </nav>

    <div className="grid items-stretch gap-3 xl:h-[238px] xl:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]"><section className="card h-full overflow-hidden p-3"><div className="mb-2 flex items-center justify-between"><div><h2 className="text-sm font-semibold">继续阅读</h2><p className="text-[11px] text-gray-500">从上次保存的 PDF 页码继续</p></div>{data.recent_reading.length > 2 ? <button type="button" className="text-xs text-primary-600 hover:underline" onClick={() => setShowAllReading((value) => !value)}>{showAllReading ? "收起" : "查看全部"}</button> : <Link to="/library?reading_status=reading" className="text-xs text-primary-600 hover:underline">查看全部</Link>}</div>
      {data.recent_reading.length ? <div className={`grid gap-2 md:grid-cols-2 ${showAllReading ? "max-h-[180px] overflow-y-auto pr-1" : ""}`}>{data.recent_reading.slice(0, showAllReading ? data.recent_reading.length : 2).map((item) => <article key={item.document_id} className={`rounded-lg border border-gray-200 p-3 dark:border-slate-700 ${data.recent_reading.length === 1 ? "md:col-span-2" : ""}`}><h3 className="line-clamp-2 min-h-9 text-xs font-medium">{item.title}</h3><p className="truncate text-[11px] text-gray-500">{item.author || "作者未知"}{item.publication_year ? ` · ${item.publication_year}` : ""}</p><div className="mt-2 h-1 overflow-hidden rounded-full bg-gray-100 dark:bg-slate-700"><div className="h-full rounded-full bg-primary-500" style={{ width: `${Math.round(item.progress_ratio * 100)}%` }} /></div><div className="mt-2 flex items-center justify-between text-[11px] text-gray-500"><span>第 {item.current_page} / {item.total_pages} 页 · {Math.round(item.progress_ratio * 100)}%</span><Link className="font-medium text-primary-600 hover:underline" to={`/reader/${item.paper_id}?document_id=${item.document_id}`}>继续阅读 →</Link></div></article>)}</div> : <Empty text="还没有阅读记录，打开一篇 PDF 开始阅读吧。" />}
    </section>

    <section className="card h-full overflow-hidden p-3"><div className="flex items-center justify-between gap-3"><div><h2 className="text-sm font-semibold">阅读趋势</h2><p className="text-[11px] text-gray-500">每日阅读活动</p></div><div className="flex items-center gap-2"><div className="flex rounded-lg bg-gray-100 p-0.5 dark:bg-slate-800" aria-label="趋势指标">{([{"key":"papers","label":"篇次"},{"key":"time","label":"时长"}] as const).map((item) => <button key={item.key} type="button" aria-pressed={trendMetric === item.key} className={`rounded-md px-2 py-0.5 text-[11px] ${trendMetric === item.key ? "bg-white font-medium text-primary-600 shadow-sm dark:bg-slate-700" : "text-gray-500"}`} onClick={() => setTrendMetric(item.key)}>{item.label}</button>)}</div><div className="flex rounded-lg bg-gray-100 p-0.5 dark:bg-slate-800">{([7, 30, 90] as const).map((days) => <button key={days} className={`rounded-md px-2 py-0.5 text-[11px] ${trendDays === days ? "bg-white font-medium text-primary-600 shadow-sm dark:bg-slate-700" : "text-gray-500"}`} onClick={() => setTrendDays(days)}>{days} 天</button>)}</div></div></div>
      {trend.isLoading ? <div className="flex h-36 items-center justify-center text-xs text-gray-400"><Loader2 className="mr-2 h-4 w-4 animate-spin" />加载趋势…</div> : trend.data ? <><ReadingTrendChart trend={trend.data} metric={trendMetric} /><p className="text-xs text-gray-500">阅读 <strong className="text-gray-800 dark:text-gray-100">{trend.data.summary.papers_read}</strong> 篇次 · 时长 <strong className="text-gray-800 dark:text-gray-100">{Math.round(trend.data.summary.reading_time_seconds / 60)}</strong> 分钟 · 活跃 <strong className="text-gray-800 dark:text-gray-100">{trend.data.summary.active_days}</strong> 天</p></> : <Empty text="趋势数据暂时不可用。" />}
    </section></div>

    <div className="grid gap-3 md:grid-cols-2 xl:h-[238px] xl:grid-cols-[minmax(0,1.05fr)_minmax(0,1fr)_minmax(0,0.9fr)]"><section className="card h-full overflow-hidden border-t-2 border-t-blue-400 p-3"><div className="flex shrink-0 flex-wrap items-center justify-between gap-1"><h2 className="text-sm font-semibold">研究主题</h2><div className="flex items-center gap-1"><select aria-label="主题统计时间范围" className="rounded-md border border-gray-200 bg-white px-1 py-0.5 text-[10px] dark:border-slate-700 dark:bg-slate-800" value={topicDays} onChange={(event) => setTopicDays(Number(event.target.value) as 7 | 30)}><option value={7}>近一周</option><option value={30}>近一月</option></select><select aria-label="主题显示数量" className="rounded-md border border-gray-200 bg-white px-1 py-0.5 text-[10px] dark:border-slate-700 dark:bg-slate-800" value={topicLimit} onChange={(event) => setTopicLimit(Number(event.target.value) as 20 | 50)}><option value={20}>20 个</option><option value={50}>50 个</option></select><div className="flex rounded-lg bg-gray-100 p-0.5 dark:bg-slate-800">{([{"key":"tag","label":"标签"},{"key":"keyword","label":"关键词"}] as const).map((item) => <button key={item.key} type="button" aria-pressed={topicType === item.key} className={`rounded-md px-2 py-0.5 text-[11px] ${topicType === item.key ? "bg-white font-medium text-primary-600 shadow-sm dark:bg-slate-700" : "text-gray-500"}`} onClick={() => setTopicType(item.key)}>{item.label}</button>)}</div></div></div><TopicCloud topics={topicType === "tag" ? data.tags : data.keywords} type={topicType} /></section>
      <DashboardSplitSlot><section className="card flex min-h-0 flex-col overflow-hidden p-3"><div className="mb-1 flex h-6 shrink-0 items-center justify-between"><h2 className="text-sm font-semibold">最近论文</h2><Link to="/library" className="text-[11px] text-primary-600 hover:underline">查看全部</Link></div>{data.recent_papers.length ? <div className="min-h-0 flex-1 divide-y divide-gray-100 overflow-y-auto dark:divide-slate-800">{data.recent_papers.slice(0, 3).map((paper) => <Link key={paper.id} to={`/reader/${paper.id}`} title={paper.title} className="flex items-center justify-between gap-2 py-1.5 first:pt-0"><div className="min-w-0"><p className="line-clamp-2 text-xs font-medium leading-4 hover:text-primary-600">{paper.title}</p><p className="truncate text-[10px] text-gray-500">{paper.author || "作者未知"}{paper.publication_year ? ` · ${paper.publication_year}` : ""}</p></div><span className="shrink-0 rounded-full bg-gray-100 px-1.5 py-0.5 text-[10px] text-gray-600 dark:bg-slate-800 dark:text-gray-300">{STATUS_LABELS[paper.reading_status] ?? paper.reading_status}</span></Link>)}</div> : <Empty text="暂无论文" />}</section><TodoWidget/></DashboardSplitSlot>
      <DashboardSplitSlot><section className="card flex min-h-0 flex-col overflow-hidden p-3"><div className="mb-1 flex h-6 shrink-0 items-center justify-between"><h2 className="text-sm font-semibold">最近笔记</h2><Link to="/notes" className="text-[11px] text-primary-600 hover:underline">查看全部</Link></div>{data.recent_notes.length ? <div className="min-h-0 flex-1 divide-y divide-gray-100 overflow-y-auto dark:divide-slate-800">{data.recent_notes.slice(0, 4).map((note) => <Link key={note.id} to={`/notes/${note.id}`} title={`${note.title} · ${note.paper_title||"独立笔记"}`} className="flex items-center justify-between gap-2 py-1.5 first:pt-0"><div className="min-w-0"><p className="truncate text-xs font-medium hover:text-primary-600">{note.title}</p><p className="truncate text-[10px] text-gray-500">{note.paper_title || "独立笔记"} · {formatTime(note.updated_at)}</p></div><span className="shrink-0 rounded-full bg-violet-50 px-1.5 py-0.5 text-[10px] text-violet-600 dark:bg-violet-950/40 dark:text-violet-300">{NOTE_LABELS[note.note_type] ?? note.note_type}</span></Link>)}</div> : <Empty text="暂无笔记" />}</section><MemoWidget/></DashboardSplitSlot></div>
    {showImportModal && <ImportModal onClose={() => setShowImportModal(false)} />}
  </div>;
}

function Empty({ text }: { text: string }) {
  return <div className="flex min-h-24 items-center justify-center rounded-lg border border-dashed border-gray-200 px-4 text-center text-sm text-gray-400 dark:border-slate-700">{text}</div>;
}
