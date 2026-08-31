import type { PaperListParams, PaperProcessingStatus, PaperReadingStatus } from "@/features/paper/types";

export interface LibraryQuery {
  q?: string;
  tag_id?: string;
  folder_id?: string;
  year?: number;
  starred?: boolean;
  status?: PaperProcessingStatus;
  reading_status?: PaperReadingStatus;
  author_role?: "first" | "corresponding" | "other";
  page: number;
  page_size: number;
}

const DEFAULT_PAGE_SIZE = 20;
const PAGE_SIZES = new Set([10, 20, 50, 100]);
const PROCESSING_STATUSES = new Set<PaperProcessingStatus>(["imported", "processing", "ready", "failed"]);
const READING_STATUSES = new Set<PaperReadingStatus>(["unread", "reading", "finished", "archived"]);
const AUTHOR_ROLES = new Set(["first", "corresponding", "other"]);

export function parseLibraryQuery(searchParams: URLSearchParams): LibraryQuery {
  const rawYear = Number(searchParams.get("year"));
  const rawPage = Number(searchParams.get("page"));
  const rawPageSize = Number(searchParams.get("page_size"));
  const rawStatus = searchParams.get("status");
  const rawReadingStatus = searchParams.get("reading_status");
  return {
    q: searchParams.get("q")?.trim() || undefined,
    tag_id: searchParams.get("tag_id") || undefined,
    folder_id: searchParams.get("folder_id") || undefined,
    year: Number.isInteger(rawYear) && rawYear >= 1000 && rawYear <= 9999 ? rawYear : undefined,
    starred: searchParams.get("starred") === "true" ? true : undefined,
    status: rawStatus && PROCESSING_STATUSES.has(rawStatus as PaperProcessingStatus) ? rawStatus as PaperProcessingStatus : undefined,
    reading_status: rawReadingStatus && READING_STATUSES.has(rawReadingStatus as PaperReadingStatus) ? rawReadingStatus as PaperReadingStatus : undefined,
    author_role: AUTHOR_ROLES.has(searchParams.get("author_role") ?? "") ? searchParams.get("author_role") as LibraryQuery["author_role"] : undefined,
    page: Number.isInteger(rawPage) && rawPage > 0 ? rawPage : 1,
    page_size: PAGE_SIZES.has(rawPageSize) ? rawPageSize : DEFAULT_PAGE_SIZE,
  };
}

export function toPaperListParams(query: LibraryQuery): PaperListParams {
  return {
    q: query.q,
    tag_id: query.tag_id,
    folder_id: query.folder_id,
    year: query.year,
    starred: query.starred,
    status: query.status,
    reading_status: query.reading_status,
    page: query.page,
    page_size: query.page_size,
    mine: true,
    author_role: query.author_role,
  };
}

export function updateLibraryQuery(current: URLSearchParams, patch: Partial<LibraryQuery>, resetPage = true): URLSearchParams {
  const next = new URLSearchParams(current);
  const merged = { ...parseLibraryQuery(current), ...patch };
  const values: Record<keyof Omit<LibraryQuery, "page" | "page_size">, string | undefined> = {
    q: merged.q,
    tag_id: merged.tag_id,
    folder_id: merged.folder_id,
    year: merged.year?.toString(),
    starred: merged.starred ? "true" : undefined,
    status: merged.status,
    reading_status: merged.reading_status,
    author_role: merged.author_role,
  };
  for (const [key, value] of Object.entries(values)) {
    if (value) next.set(key, value); else next.delete(key);
  }
  const page = resetPage ? 1 : merged.page;
  if (page === 1) next.delete("page"); else next.set("page", String(page));
  if (merged.page_size === DEFAULT_PAGE_SIZE) next.delete("page_size"); else next.set("page_size", String(merged.page_size));
  return next;
}

export function clearLibraryFilters(): URLSearchParams {
  return new URLSearchParams();
}
