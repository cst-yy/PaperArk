import type { PaperListQuery, PaperListSort, SortOrder } from "./types";

const sorts = new Set<PaperListSort>(["title", "title_zh", "publication_year", "journal", "conference", "citation_count", "reading_status", "created_at", "updated_at"]);
const sizes = new Set([25, 50, 100, 200]);
const readings = new Set(["unread", "reading", "finished", "archived"]);
const number = (value: string | null, min: number, max: number) => { const parsed = Number(value); return Number.isInteger(parsed) && parsed >= min && parsed <= max ? parsed : undefined; };

export function parsePaperListQuery(params: URLSearchParams): PaperListQuery {
  const sort = params.get("sort") as PaperListSort;
  const order = params.get("order") as SortOrder;
  const pageSize = Number(params.get("page_size"));
  const reading = params.get("reading_status");
  return { q: params.get("q")?.trim() || undefined, year_from: number(params.get("year_from"), 1000, 9999), year_to: number(params.get("year_to"), 1000, 9999),
    journal: params.get("journal")?.trim() || undefined, author: params.get("author")?.trim() || undefined, tag_id: params.get("tag_id") || undefined,
    keyword: params.get("keyword")?.trim() || undefined, reading_status: reading && readings.has(reading) ? reading : undefined,
    starred: params.get("starred") === "true" ? true : undefined, sort: sorts.has(sort) ? sort : "updated_at", order: order === "asc" ? "asc" : "desc",
    page: number(params.get("page"), 1, 1_000_000) ?? 1, page_size: (sizes.has(pageSize) ? pageSize : 50) as 25 | 50 | 100 | 200 };
}

export function patchPaperListQuery(current: URLSearchParams, patch: Partial<PaperListQuery>, resetPage = true) {
  const merged = { ...parsePaperListQuery(current), ...patch, page: resetPage ? 1 : (patch.page ?? parsePaperListQuery(current).page) };
  const next = new URLSearchParams();
  for (const [key, value] of Object.entries(merged)) {
    if (value !== undefined && value !== false && !(key === "page" && value === 1) && !(key === "page_size" && value === 50) && !(key === "sort" && value === "updated_at") && !(key === "order" && value === "desc")) next.set(key, String(value));
  }
  return next;
}

export function serializePaperListQuery(query: PaperListQuery): URLSearchParams {
  const next = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) if (value !== undefined && value !== false && value !== null) next.set(key, String(value));
  return next;
}
