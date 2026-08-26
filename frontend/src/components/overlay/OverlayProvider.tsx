/* eslint-disable react-refresh/only-export-components -- provider and its contract are one overlay primitive */
import { createContext, useCallback, useEffect, useMemo, useRef, type ReactNode, type RefObject } from "react";

export type OverlayDismissReason = "outside-pointer" | "escape" | "sibling-open" | "navigation";

interface OverlayEntry {
  id: string;
  group: string;
  parentId?: string;
  triggerRef: RefObject<HTMLElement | null>;
  contentRef: RefObject<HTMLElement | null>;
  onDismiss: (reason: OverlayDismissReason) => void;
}

interface OverlayStack {
  register: (entry: OverlayEntry) => () => void;
}

export const OverlayContext = createContext<OverlayStack | null>(null);

function eventPath(event: Event): EventTarget[] {
  return typeof event.composedPath === "function" ? event.composedPath() : event.target ? [event.target] : [];
}

function entryContains(entry: OverlayEntry, path: EventTarget[]) {
  return path.includes(entry.triggerRef.current as EventTarget) || path.includes(entry.contentRef.current as EventTarget);
}

function lastContainingIndex(entries: OverlayEntry[], path: EventTarget[]) {
  for (let index = entries.length - 1; index >= 0; index -= 1) if (entryContains(entries[index], path)) return index;
  return -1;
}

export function OverlayProvider({ children }: { children: ReactNode }) {
  const entries = useRef<OverlayEntry[]>([]);
  const pointerDownPath = useRef<EventTarget[] | null>(null);

  const register = useCallback((entry: OverlayEntry) => {
    const siblings = entries.current.filter((candidate) => candidate.id !== entry.id && candidate.group === entry.group && candidate.parentId === entry.parentId);
    siblings.reverse().forEach((candidate) => candidate.onDismiss("sibling-open"));
    entries.current = [...entries.current.filter((candidate) => candidate.id !== entry.id), entry];
    return () => { entries.current = entries.current.filter((candidate) => candidate.id !== entry.id); };
  }, []);

  useEffect(() => {
    const onPointerDown = (event: PointerEvent) => { pointerDownPath.current = eventPath(event); };
    const onPointerUp = (event: PointerEvent) => {
      const downPath = pointerDownPath.current;
      pointerDownPath.current = null;
      if (!downPath) return;
      const upPath = eventPath(event);
      const snapshot = [...entries.current];
      const downInside = lastContainingIndex(snapshot, downPath);
      const upInside = lastContainingIndex(snapshot, upPath);
      if (downInside !== upInside) return;
      for (let index = snapshot.length - 1; index > downInside; index -= 1) snapshot[index].onDismiss("outside-pointer");
    };
    const onPointerCancel = () => { pointerDownPath.current = null; };
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      const top = entries.current[entries.current.length - 1];
      if (!top) return;
      event.preventDefault();
      event.stopPropagation();
      top.onDismiss("escape");
    };
    const onPopState = () => [...entries.current].reverse().forEach((entry) => entry.onDismiss("navigation"));
    document.addEventListener("pointerdown", onPointerDown, true);
    document.addEventListener("pointerup", onPointerUp, true);
    document.addEventListener("pointercancel", onPointerCancel, true);
    document.addEventListener("keydown", onKeyDown, true);
    window.addEventListener("popstate", onPopState);
    return () => {
      document.removeEventListener("pointerdown", onPointerDown, true);
      document.removeEventListener("pointerup", onPointerUp, true);
      document.removeEventListener("pointercancel", onPointerCancel, true);
      document.removeEventListener("keydown", onKeyDown, true);
      window.removeEventListener("popstate", onPopState);
    };
  }, []);

  const value = useMemo(() => ({ register }), [register]);
  return <OverlayContext.Provider value={value}>{children}</OverlayContext.Provider>;
}
