import { Link } from "react-router-dom";
import { Pencil, Star, FileText, FileType } from "lucide-react";
import clsx from "clsx";
import type { ReactNode } from "react";
import type { PaperListItem } from "@/features/paper/types";
import { getStableColor } from "@/utils";

interface PaperCardProps {
  paper: PaperListItem;
  onToggleStar?: (id: string) => void;
  onEdit?: (id: string) => void;
}

const PROCESSING_STATUS_LABELS: Record<string, string> = {
  imported: "已导入",
  processing: "解析中",
  ready: "就绪",
  failed: "失败",
};

const READING_STATUS_LABELS: Record<string, string> = {
  unread: "未读",
  reading: "阅读中",
  finished: "已读",
  archived: "已归档",
};

export function PaperCard({ paper, onToggleStar, onEdit }: PaperCardProps) {
  // Build source info: "Neurocomputing · 2025" or "ICML 2025" or just "2025"
  const sourceParts: string[] = [];
  if (paper.journal) sourceParts.push(paper.journal);
  else if (paper.conference) sourceParts.push(paper.conference);
  if (paper.publication_year) sourceParts.push(String(paper.publication_year));
  const source = sourceParts.join(" · ");

  // Author display: "Yu Yang, ..." → first author only
  const authorDisplay = paper.first_author
    ? `${paper.first_author}${paper.first_author.includes(",") ? " et al." : ""}`
    : null;

  // Has PDF attached?
  const hasPdf = paper.has_document ?? false;

  return (
    <div className="card flex items-start gap-3 hover:shadow-md transition-shadow">
      {hasPdf ? (
        <FileType className="mt-0.5 h-5 w-5 shrink-0 text-primary-500" />
      ) : (
        <FileText className="mt-0.5 h-5 w-5 shrink-0 text-gray-300" />
      )}

      <div className="flex-1 min-w-0">
        <Link
          to={hasPdf ? `/reader/${paper.id}` : "#"}
          className={clsx(
            "text-sm font-medium line-clamp-2",
            hasPdf
              ? "text-gray-900 hover:text-primary-500"
              : "text-gray-500"
          )}
        >
          {paper.title}
        </Link>
        {paper.title_zh && <p className="mt-1 line-clamp-1 text-xs text-gray-500 dark:text-gray-400">{paper.title_zh}</p>}

        <div className="mt-1 flex items-center gap-2 text-xs text-gray-500">
          {source && <span>{source}</span>}
          {authorDisplay && <span>· {authorDisplay}</span>}
          {hasPdf && <span className="text-primary-400">· 有 PDF</span>}
          <span
            className={clsx(
              "rounded px-1.5 py-0.5 text-[10px] font-medium",
              paper.status === "ready" && "bg-green-50 text-green-600",
              paper.status === "processing" && "bg-amber-50 text-amber-600",
              paper.status === "imported" && "bg-blue-50 text-blue-600",
              paper.status === "failed" && "bg-red-50 text-red-600"
            )}
          >
            {PROCESSING_STATUS_LABELS[paper.status] || paper.status}
          </span>
          <span
            className={clsx(
              "rounded px-1.5 py-0.5 text-[10px] font-medium",
              paper.reading_status === "unread" && "bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-200",
              paper.reading_status === "reading" && "bg-primary-50 text-primary-600 dark:bg-primary-950 dark:text-primary-300",
              paper.reading_status === "finished" && "bg-emerald-50 text-emerald-600 dark:bg-emerald-950 dark:text-emerald-300",
              paper.reading_status === "archived" && "bg-gray-100 text-gray-500 dark:bg-slate-800 dark:text-gray-400"
            )}
          >
            {READING_STATUS_LABELS[paper.reading_status] || paper.reading_status}
          </span>
        </div>

        {paper.my_author_roles && <div className="mt-2 flex flex-wrap gap-1">
          {paper.my_author_roles.is_first_author && <RoleBadge>第一作者</RoleBadge>}
          {paper.my_author_roles.is_co_first && <RoleBadge>共同一作</RoleBadge>}
          {paper.my_author_roles.is_corresponding && <RoleBadge>通讯作者</RoleBadge>}
          {!paper.my_author_roles.is_first_author && !paper.my_author_roles.is_co_first && !paper.my_author_roles.is_corresponding && <RoleBadge>第 {paper.my_author_roles.author_order + 1} 作者</RoleBadge>}
        </div>}

        {paper.tags.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1">
            {paper.tags.map((tag) => (
              <span
                key={tag.id}
                className="rounded px-1.5 py-0.5 text-[10px] text-white"
                style={{
                  backgroundColor: tag.color || getStableColor(tag.name),
                }}
              >
                {tag.name}
              </span>
            ))}
          </div>
        )}
        {paper.keywords?.length ? <div className="mt-1 flex flex-wrap gap-1">{paper.keywords.slice(0,4).map(keyword=><span key={keyword.id} className="rounded bg-sky-50 px-1.5 py-0.5 text-[10px] text-sky-700 dark:bg-sky-950/40 dark:text-sky-300">{keyword.display_name}</span>)}</div>:null}
      </div>

      <div className="flex shrink-0 items-center gap-1"><button type="button" onClick={() => onEdit?.(paper.id)} className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-primary-600 dark:hover:bg-slate-800" aria-label="编辑论文信息" title="编辑信息"><Pencil className="h-4 w-4" /></button><button type="button" onClick={() => onToggleStar?.(paper.id)} className="p-1" aria-label="收藏论文"><Star className={clsx("h-4 w-4", paper.is_starred ? "fill-amber-400 text-amber-400" : "text-gray-300")} /></button></div>
    </div>
  );
}

function RoleBadge({children}:{children:ReactNode}) { return <span className="rounded-full bg-violet-50 px-2 py-0.5 text-[10px] font-medium text-violet-700 dark:bg-violet-950/40 dark:text-violet-300">{children}</span>; }
