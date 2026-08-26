import { ArrowRight, BookOpen, ChevronDown, ChevronUp } from "lucide-react";
import { Link } from "react-router-dom";

import type { RecentReadingItem } from "./types";

interface RecentReadingListProps {
  items: RecentReadingItem[];
  isLoading: boolean;
  expanded: boolean;
  onToggleExpanded: () => void;
}

export function RecentReadingList({ items, isLoading, expanded, onToggleExpanded }: RecentReadingListProps) {
  return (
    <section className="mb-6 rounded-xl border border-gray-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-900">
      <div className="mb-3 flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold text-gray-900 dark:text-gray-100">最近阅读</h2>
          <p className="mt-0.5 text-xs text-gray-500 dark:text-gray-400">从上次阅读的位置继续</p>
        </div>
        <div className="flex items-center gap-2">
          <BookOpen className="h-5 w-5 text-primary-500" />
          <button
            type="button"
            aria-expanded={expanded}
            aria-label={expanded ? "收起最近阅读" : "展开最多 10 条最近阅读"}
            className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs font-medium text-gray-500 hover:bg-gray-100 hover:text-gray-700 dark:text-gray-400 dark:hover:bg-slate-800 dark:hover:text-gray-200"
            onClick={onToggleExpanded}
          >
            {expanded ? "收起" : "查看更多"}
            {expanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
          </button>
        </div>
      </div>

      {isLoading ? (
        <div className="py-5 text-center text-sm text-gray-400">正在加载最近阅读…</div>
      ) : items.length === 0 ? (
        <div className="rounded-lg bg-gray-50 px-4 py-5 text-center dark:bg-slate-800">
          <p className="text-sm font-medium text-gray-600 dark:text-gray-200">暂无最近阅读</p>
          <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">打开一篇 PDF 开始阅读后，这里会显示你的阅读进度。</p>
        </div>
      ) : (
        <div className="grid gap-3 md:grid-cols-2">
          {items.map((item) => <RecentReadingCard key={item.document.id} item={item} />)}
        </div>
      )}
    </section>
  );
}

function RecentReadingCard({ item }: { item: RecentReadingItem }) {
  const percentage = Math.round(item.progress_ratio * 100);
  const authorText = item.paper.authors.slice(0, 2).join("、");
  const sourceText = [authorText, item.paper.publication_year].filter(Boolean).join(" · ");
  const href = `/reader/${item.paper.id}?document_id=${encodeURIComponent(item.document.id)}`;

  return (
    <article className="rounded-lg border border-gray-100 p-3 dark:border-slate-700">
      <h3 className="line-clamp-2 text-sm font-medium text-gray-900 dark:text-gray-100">{item.paper.title}</h3>
      {sourceText && <p className="mt-1 truncate text-xs text-gray-500 dark:text-gray-400">{sourceText}</p>}
      <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-gray-100 dark:bg-slate-700">
        <div className="h-full rounded-full bg-primary-500" style={{ width: `${Math.min(100, Math.max(0, percentage))}%` }} />
      </div>
      <div className="mt-2 flex items-center justify-between gap-3 text-xs text-gray-500 dark:text-gray-400">
        <span>第 {item.current_page} / {item.total_pages} 页 · {percentage}%</span>
        <span>{formatRecentTime(item.last_read_at)}</span>
      </div>
      <Link to={href} className="mt-3 inline-flex items-center gap-1 text-xs font-medium text-primary-600 hover:text-primary-700 dark:text-primary-400">
        继续阅读 <ArrowRight className="h-3.5 w-3.5" />
      </Link>
    </article>
  );
}

function formatRecentTime(value: string): string {
  const date = new Date(value);
  const elapsedMs = Date.now() - date.getTime();
  if (elapsedMs < 60_000) return "刚刚";
  if (elapsedMs < 3_600_000) return `${Math.floor(elapsedMs / 60_000)} 分钟前`;

  const now = new Date();
  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
  const startOfYesterday = startOfToday - 86_400_000;
  if (date.getTime() >= startOfToday) {
    return `今天 ${date.toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit", hour12: false })}`;
  }
  if (date.getTime() >= startOfYesterday) return "昨天";
  return date.toLocaleDateString("zh-CN", { year: "numeric", month: "2-digit", day: "2-digit" });
}
