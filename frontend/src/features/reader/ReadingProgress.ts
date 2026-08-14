/**
 * Reading progress tracking utilities.
 * Saves to localStorage for P0; migrate to API in S6.
 */

const STORAGE_KEY = "reading_progress";

interface ProgressEntry {
  paperId: string;
  currentPage: number;
  scrollPosition: number;
  progressPercent: number;
  lastReadAt: string;
}

export function getProgress(paperId: string): ProgressEntry | null {
  const all = getAllProgress();
  return all[paperId] || null;
}

export function saveProgress(entry: ProgressEntry): void {
  const all = getAllProgress();
  all[entry.paperId] = entry;
  localStorage.setItem(STORAGE_KEY, JSON.stringify(all));
}

export function getAllProgress(): Record<string, ProgressEntry> {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
}

export function getRecentlyRead(limit: number = 5): ProgressEntry[] {
  const all = getAllProgress();
  return Object.values(all)
    .sort((a, b) => new Date(b.lastReadAt).getTime() - new Date(a.lastReadAt).getTime())
    .slice(0, limit);
}

export function calculateProgress(currentPage: number, totalPages: number): number {
  if (totalPages === 0) return 0;
  return Math.min(100, Math.round((currentPage / totalPages) * 100));
}
