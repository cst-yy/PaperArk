import { create } from "zustand";

/**
 * Client-only paper UI state.
 *
 * Paper lists and paper details are server state and belong to React Query;
 * keeping a second Zustand copy leads to stale Library/Dashboard views after
 * upload, delete, or invalidation.
 */
interface PaperUIState {
  selectedPaperId: string | null;
  setSelectedPaper: (id: string | null) => void;
}

export const usePaperStore = create<PaperUIState>((set) => ({
  selectedPaperId: null,
  setSelectedPaper: (id) => set({ selectedPaperId: id }),
}));
