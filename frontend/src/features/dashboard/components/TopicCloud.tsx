import { useLayoutEffect, useRef } from "react";
import { Link } from "react-router-dom";
import type { DashboardTopicStat } from "../types";

export function TopicCloud({ topics, type }: { topics: DashboardTopicStat[]; type: "tag" | "keyword" }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const contentRef = useRef<HTMLDivElement>(null);
  const max = Math.max(...topics.map((topic) => topic.paper_count), 1);
  const size = (count: number) => 12 + (Math.log1p(count) / Math.log1p(max)) * 9;
  const hash = (value: string) => Array.from(value).reduce((result, char) => ((result * 31) + char.charCodeAt(0)) >>> 0, 7);
  const arranged = [...topics].sort((left, right) => hash(`${type}:${left.id}`) - hash(`${type}:${right.id}`));
  const tagColors = ["text-blue-600", "text-cyan-600", "text-teal-600", "text-sky-600", "text-indigo-600"];
  const keywordColors = ["text-violet-600", "text-fuchsia-600", "text-rose-600", "text-amber-600", "text-purple-600"];
  const colors = type === "tag" ? tagColors : keywordColors;
  useLayoutEffect(() => {
    const container = containerRef.current;
    const content = contentRef.current;
    if (!container || !content) return;
    const fit = () => {
      container.style.setProperty("--topic-scale", "1");
      const widthRatio = container.clientWidth / Math.max(content.scrollWidth, 1);
      const heightRatio = container.clientHeight / Math.max(content.scrollHeight, 1);
      const scale = Math.max(0.32, Math.min(1, widthRatio, heightRatio) * 0.96);
      container.style.setProperty("--topic-scale", String(scale));
    };
    const observer = new ResizeObserver(fit);
    observer.observe(container);
    fit();
    return () => observer.disconnect();
  }, [topics, type]);
  if (!topics.length) return <p className="py-8 text-center text-sm text-gray-400">暂无主题数据</p>;
  return <div ref={containerRef} className="min-h-0 flex-1 overflow-hidden px-1 py-2"><div ref={contentRef} className="flex min-h-full flex-wrap content-center items-center justify-center gap-x-3 gap-y-1.5 text-center">
    {arranged.map((topic) => <Link key={topic.id} to={type === "tag" ? `/library?tag_id=${topic.id}` : `/library?q=${encodeURIComponent(topic.name)}`} className={`max-w-full break-words rounded-lg px-1.5 py-0.5 font-medium leading-tight transition-transform hover:-translate-y-0.5 hover:bg-gray-50 dark:hover:bg-slate-800 ${colors[hash(topic.id) % colors.length]}`} style={{ fontSize: `calc(${size(topic.paper_count)}px * var(--topic-scale, 1))` }} title={`${topic.name} · ${topic.paper_count} 篇论文`}>{topic.name}</Link>)}
  </div></div>;
}
