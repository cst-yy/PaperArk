import type { ReadingTrend } from "../types";

export type TrendMetric = "papers" | "time";

export function ReadingTrendChart({ trend, metric }: { trend: ReadingTrend; metric: TrendMetric }) {
  const width = 720;
  const height = 180;
  const padding = 24;
  const maxPapers = Math.max(...trend.daily.map((item) => item.papers_read), 1);
  const maxMinutes = Math.max(...trend.daily.map((item) => item.reading_time_seconds / 60), 1);
  const points = trend.daily.map((item, index) => ({
    ...item,
    x: padding + (index / Math.max(trend.daily.length - 1, 1)) * (width - padding * 2),
    paperY: height - padding - (item.papers_read / maxPapers) * (height - padding * 2),
    timeY: height - padding - (item.reading_time_seconds / 60 / maxMinutes) * (height - padding * 2),
  }));
  const path = points.map((point, index) => `${index ? "L" : "M"}${point.x},${metric === "papers" ? point.paperY : point.timeY}`).join(" ");
  const labelStep = trend.days === 7 ? 1 : trend.days === 30 ? 5 : 15;

  return <div className="overflow-hidden">
    <svg viewBox={`0 0 ${width} ${height}`} className="h-[158px] w-full" role="img" aria-label={`过去 ${trend.days} 天${metric === "papers" ? "阅读篇次" : "阅读时长"}趋势`}>
      {[0.25, 0.5, 0.75].map((ratio) => <line key={ratio} x1={padding} y1={padding + ratio * (height - padding * 2)} x2={width - padding} y2={padding + ratio * (height - padding * 2)} stroke="currentColor" strokeDasharray="3 7" className="text-gray-100 dark:text-slate-800" />)}
      <line x1={padding} y1={height - padding} x2={width - padding} y2={height - padding} stroke="currentColor" className="text-gray-200 dark:text-slate-700" />
      <path d={path} fill="none" stroke="currentColor" strokeWidth="3" strokeLinejoin="round" className={metric === "papers" ? "text-blue-500" : "text-orange-500"} />
      {points.map((point, index) => <g key={point.date}>
        <circle cx={point.x} cy={metric === "papers" ? point.paperY : point.timeY} r={(metric === "papers" ? point.papers_read : point.reading_time_seconds) ? 4 : 2.5} fill="currentColor" className={(metric === "papers" ? point.papers_read : point.reading_time_seconds) ? (metric === "papers" ? "text-blue-500" : "text-orange-500") : "text-gray-300 dark:text-slate-600"}><title>{metric === "papers" ? `${point.date}：阅读 ${point.papers_read} 篇次` : `${point.date}：阅读 ${Math.round(point.reading_time_seconds / 60)} 分钟`}</title></circle>
        {(index % labelStep === 0 || index === points.length - 1) && <text x={point.x} y={height - 5} textAnchor="middle" className="fill-gray-400 text-[10px]">{point.date.slice(5)}</text>}
      </g>)}
    </svg>
  </div>;
}
