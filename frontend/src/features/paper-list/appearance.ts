export type PaperListFont = "system" | "Arial" | "Helvetica" | "Times New Roman" | "Georgia" | "Noto Sans" | "Noto Serif";
export type PaperListFontSize = "small" | "normal" | "large";
export type PaperListDensity = "compact" | "normal" | "relaxed";

export interface PaperListAppearance {
  font_family: PaperListFont; font_size: PaperListFontSize; density: PaperListDensity;
  header_background: string; header_text: string; row_background: string;
  alternate_row_background: string; selected_background: string; hover_background: string;
  primary_text: string; secondary_text: string; border: string; link: string;
}

export const DEFAULT_APPEARANCE: PaperListAppearance = {
  font_family: "system", font_size: "normal", density: "compact",
  header_background: "#F8FAFC", header_text: "#475569", row_background: "#FFFFFF",
  alternate_row_background: "#F8FAFC", selected_background: "#E0E7FF", hover_background: "#EEF2FF",
  primary_text: "#0F172A", secondary_text: "#64748B", border: "#E2E8F0", link: "#4F46E5",
};
export const FONT_MAP: Record<PaperListFont, string> = {
  system: "ui-sans-serif, system-ui, sans-serif", Arial: "Arial, sans-serif", Helvetica: "Helvetica, Arial, sans-serif",
  "Times New Roman": "'Times New Roman', serif", Georgia: "Georgia, serif", "Noto Sans": "'Noto Sans', sans-serif", "Noto Serif": "'Noto Serif', serif",
};
export const FONT_SIZE = { small: 12, normal: 14, large: 16 } as const;
export const ROW_HEIGHT = { compact: 38, normal: 46, relaxed: 54 } as const;
export const isHexColor = (value: string) => /^#[0-9a-f]{6}$/i.test(value);
