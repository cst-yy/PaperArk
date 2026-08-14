import type { NormalizedRect } from "@/features/annotation/types";

const clamp = (value: number) => Math.max(0, Math.min(1, value));

export function normalizeClientRect(rect: DOMRect, pageRect: DOMRect): NormalizedRect | null {
  if (!pageRect.width || !pageRect.height || rect.width <= 0 || rect.height <= 0) return null;

  const x = clamp((rect.left - pageRect.left) / pageRect.width);
  const y = clamp((rect.top - pageRect.top) / pageRect.height);
  const right = clamp((rect.right - pageRect.left) / pageRect.width);
  const bottom = clamp((rect.bottom - pageRect.top) / pageRect.height);
  if (right <= x || bottom <= y) return null;

  return {
    x: Number(x.toFixed(6)),
    y: Number(y.toFixed(6)),
    width: Number((right - x).toFixed(6)),
    height: Number((bottom - y).toFixed(6)),
  };
}

export function mergeSelectionRects(rects: NormalizedRect[]): NormalizedRect[] {
  const sorted = [...rects].sort((a, b) => a.y - b.y || a.x - b.x);
  return sorted.reduce<NormalizedRect[]>((merged, rect) => {
    const previous = merged[merged.length - 1];
    const sameLine = previous && Math.abs(previous.y - rect.y) < 0.008 && Math.abs(previous.height - rect.height) < 0.012;
    const nearHorizontally = previous && rect.x - (previous.x + previous.width) < 0.018;
    if (previous && sameLine && nearHorizontally) {
      previous.width = Number((Math.max(previous.x + previous.width, rect.x + rect.width) - previous.x).toFixed(6));
      previous.height = Number((Math.max(previous.y + previous.height, rect.y + rect.height) - previous.y).toFixed(6));
    } else {
      merged.push({ ...rect });
    }
    return merged;
  }, []);
}
