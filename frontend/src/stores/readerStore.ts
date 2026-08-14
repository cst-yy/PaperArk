import { create } from "zustand";

import type { ZoomMode } from "@/features/reader/readerTypes";

type ReaderSidebarTab = "annotations" | "ai";

const MIN_SCALE = 0.5;
const MAX_SCALE = 2.5;
const SCALE_STEP = 0.1;

const initialState = {
  currentPage: 1,
  totalPages: 0,
  scale: 1,
  zoomMode: "fit-width" as ZoomMode,
  sidebarTab: "annotations" as ReaderSidebarTab,
};

interface ReaderState {
  currentPage: number;
  totalPages: number;
  scale: number;
  zoomMode: ZoomMode;
  sidebarTab: ReaderSidebarTab;
  setCurrentPage: (page: number) => void;
  setTotalPages: (total: number) => void;
  setScale: (scale: number) => void;
  setZoomMode: (mode: ZoomMode) => void;
  setSidebarTab: (tab: ReaderSidebarTab) => void;
  nextPage: () => void;
  prevPage: () => void;
  zoomIn: () => void;
  zoomOut: () => void;
  fitWidth: () => void;
  reset: () => void;
}

export const useReaderStore = create<ReaderState>((set) => ({
  ...initialState,
  setCurrentPage: (page) =>
    set((state) => ({
      currentPage: Math.max(1, Math.min(Math.trunc(page) || 1, state.totalPages || 1)),
    })),
  setTotalPages: (total) =>
    set((state) => {
      const totalPages = Math.max(0, Math.trunc(total));
      return {
        totalPages,
        currentPage: totalPages ? Math.min(Math.max(1, state.currentPage), totalPages) : 1,
      };
    }),
  setScale: (scale) =>
    set({
      scale: Math.max(MIN_SCALE, Math.min(MAX_SCALE, scale)),
      zoomMode: "custom",
    }),
  setZoomMode: (zoomMode) => set({ zoomMode }),
  setSidebarTab: (sidebarTab) => set({ sidebarTab }),
  nextPage: () =>
    set((state) => ({
      currentPage: state.totalPages
        ? Math.min(state.currentPage + 1, state.totalPages)
        : state.currentPage,
    })),
  prevPage: () => set((state) => ({ currentPage: Math.max(1, state.currentPage - 1) })),
  zoomIn: () =>
    set((state) => ({
      scale: Math.min(MAX_SCALE, Number((state.scale + SCALE_STEP).toFixed(2))),
      zoomMode: "custom",
    })),
  zoomOut: () =>
    set((state) => ({
      scale: Math.max(MIN_SCALE, Number((state.scale - SCALE_STEP).toFixed(2))),
      zoomMode: "custom",
    })),
  fitWidth: () => set({ zoomMode: "fit-width" }),
  reset: () => set(initialState),
}));
