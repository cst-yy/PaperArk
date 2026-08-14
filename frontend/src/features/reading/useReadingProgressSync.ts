import { useCallback, useEffect, useRef } from "react";
import { useQueryClient } from "@tanstack/react-query";
import type { PDFDocumentProxy } from "pdfjs-dist";

import type { PaperReadingStatus } from "@/features/paper/types";
import { getReadingProgress, upsertReadingProgress } from "./api";

const DEBOUNCE_MS = 1000;

type Scope = {
  paperId: string;
  documentId: string;
};

type UseReadingProgressSyncOptions = {
  paperId?: string;
  documentId?: string;
  currentPage: number;
  totalPages: number;
  readingStatus?: PaperReadingStatus;
  setCurrentPage: (page: number) => void;
};

const scopeKey = (scope: Scope) => `${scope.paperId}:${scope.documentId}`;

export function useReadingProgressSync({
  paperId,
  documentId,
  currentPage,
  totalPages,
  readingStatus,
  setCurrentPage,
}: UseReadingProgressSyncOptions) {
  const queryClient = useQueryClient();
  const stateRef = useRef({
    scope: null as Scope | null,
    currentPage: 1,
    totalPages: 0,
    ready: false,
    restoredKey: null as string | null,
    statusInvalidatedKey: null as string | null,
  });
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const writeQueueRef = useRef(Promise.resolve());

  const clearTimer = useCallback(() => {
    if (timerRef.current) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  const persist = useCallback(() => {
    const { scope, currentPage: page, totalPages: pages, ready } = stateRef.current;
    if (!scope || !ready || pages < 1) return;
    const payload = {
      document_id: scope.documentId,
      current_page: Math.max(1, Math.min(page, pages)),
      total_pages: pages,
    };
    writeQueueRef.current = writeQueueRef.current
      .catch(() => undefined)
      .then(async () => {
        await upsertReadingProgress(scope.paperId, payload);
        const key = scopeKey(scope);
        if (stateRef.current.statusInvalidatedKey !== key) {
          stateRef.current.statusInvalidatedKey = key;
          await Promise.all([
            queryClient.invalidateQueries({ queryKey: ["paper", scope.paperId] }),
            queryClient.invalidateQueries({ queryKey: ["papers"] }),
          ]);
        }
      })
      .catch(() => undefined);
  }, [queryClient]);

  const flush = useCallback(() => {
    clearTimer();
    persist();
  }, [clearTimer, persist]);

  useEffect(() => {
    const state = stateRef.current;
    state.scope = paperId && documentId ? { paperId, documentId } : null;
    state.ready = false;
    state.restoredKey = null;
    state.statusInvalidatedKey = null;

    return () => {
      flush();
      state.scope = null;
      state.ready = false;
      state.restoredKey = null;
      state.statusInvalidatedKey = null;
    };
  }, [paperId, documentId, flush]);

  useEffect(() => {
    if (readingStatus !== "unread") return;
    const scope = stateRef.current.scope;
    if (!scope) return;
    const key = scopeKey(scope);
    if (stateRef.current.statusInvalidatedKey === key) {
      stateRef.current.statusInvalidatedKey = null;
    }
  }, [readingStatus]);

  useEffect(() => {
    stateRef.current.currentPage = currentPage;
    stateRef.current.totalPages = totalPages;
    if (!stateRef.current.ready || totalPages < 1) return;
    clearTimer();
    timerRef.current = setTimeout(() => {
      timerRef.current = null;
      persist();
    }, DEBOUNCE_MS);
  }, [clearTimer, currentPage, persist, totalPages]);

  useEffect(() => {
    const handleVisibilityChange = () => {
      if (document.visibilityState === "hidden") flush();
    };
    document.addEventListener("visibilitychange", handleVisibilityChange);
    return () => {
      document.removeEventListener("visibilitychange", handleVisibilityChange);
      flush();
    };
  }, [flush]);

  const restoreAfterDocumentLoad = async (pdf: PDFDocumentProxy) => {
    const scope = stateRef.current.scope;
    if (!scope || pdf.numPages < 1) return;
    const key = scopeKey(scope);
    if (stateRef.current.restoredKey === key) return;
    stateRef.current.restoredKey = key;
    stateRef.current.totalPages = pdf.numPages;
    stateRef.current.ready = false;

    try {
      const progress = await getReadingProgress(scope.paperId, scope.documentId);
      if (stateRef.current.scope && scopeKey(stateRef.current.scope) === key) {
        const page = Math.max(1, Math.min(progress?.current_page ?? 1, pdf.numPages));
        stateRef.current.currentPage = page;
        setCurrentPage(page);
      }
    } catch {
      // A transient progress lookup failure must not block the reader.
      if (stateRef.current.scope && scopeKey(stateRef.current.scope) === key) {
        stateRef.current.currentPage = 1;
        setCurrentPage(1);
      }
    } finally {
      if (stateRef.current.scope && scopeKey(stateRef.current.scope) === key) {
        stateRef.current.ready = true;
        stateRef.current.currentPage = Math.max(1, Math.min(
          stateRef.current.currentPage,
          pdf.numPages,
        ));
      }
    }
  };

  return { restoreAfterDocumentLoad, flush };
}
