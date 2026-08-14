import { useCallback } from "react";

import type { SelectionContext } from "@/features/annotation/types";
import { mergeSelectionRects, normalizeClientRect } from "@/features/reader/utils/rects";

interface UseTextSelectionOptions {
  pageNumber: number;
  pageRef: React.RefObject<HTMLDivElement>;
  onSelection: (selection: SelectionContext | null) => void;
}

export function useTextSelection({ pageNumber, pageRef, onSelection }: UseTextSelectionOptions) {
  return useCallback(() => {
    const selection = window.getSelection();
    const pageElement = pageRef.current;
    if (!selection || selection.rangeCount === 0 || !pageElement) return;

    const range = selection.getRangeAt(0);
    if (!pageElement.contains(range.commonAncestorContainer)) return;

    const text = selection.toString().replace(/\s+/g, " ").trim();
    const pageRect = pageElement.getBoundingClientRect();
    const rects = mergeSelectionRects(
      Array.from(range.getClientRects())
        .map((rect) => normalizeClientRect(rect, pageRect))
        .filter((rect): rect is NonNullable<typeof rect> => rect !== null),
    );
    if (!text || !rects.length) {
      onSelection(null);
      return;
    }

    const pageText = pageElement.textContent?.replace(/\s+/g, " ").trim() ?? "";
    const textIndex = pageText.indexOf(text);
    const toolbarRect = range.getBoundingClientRect();
    onSelection({
      pageNumber,
      text,
      prefixText: textIndex > 0 ? pageText.slice(Math.max(0, textIndex - 120), textIndex) : "",
      suffixText: textIndex >= 0 ? pageText.slice(textIndex + text.length, textIndex + text.length + 120) : "",
      rects,
      toolbarRect,
    });
  }, [onSelection, pageNumber, pageRef]);
}
