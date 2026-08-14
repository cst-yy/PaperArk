import type { Annotation } from "@/features/annotation/types";

const colorMap = {
  yellow: { highlight: "rgba(250, 204, 21, .38)", underline: "#ca8a04", area: "rgba(250, 204, 21, .18)" },
  green: { highlight: "rgba(74, 222, 128, .34)", underline: "#16a34a", area: "rgba(74, 222, 128, .16)" },
  blue: { highlight: "rgba(96, 165, 250, .34)", underline: "#2563eb", area: "rgba(96, 165, 250, .16)" },
  red: { highlight: "rgba(248, 113, 113, .34)", underline: "#dc2626", area: "rgba(248, 113, 113, .16)" },
  purple: { highlight: "rgba(192, 132, 252, .34)", underline: "#9333ea", area: "rgba(192, 132, 252, .16)" },
} as const;

interface AnnotationOverlayLayerProps {
  pageNumber: number;
  annotations: Annotation[];
  activeAnnotationId?: string | null;
  onClick?: (annotation: Annotation) => void;
}

export function AnnotationOverlayLayer({ pageNumber, annotations, activeAnnotationId, onClick }: AnnotationOverlayLayerProps) {
  return (
    <div className="pointer-events-none absolute inset-0" aria-label={`第 ${pageNumber} 页标注`}>
      {annotations
        .filter((annotation) => annotation.page_number === pageNumber && annotation.position_data)
        .flatMap((annotation) => {
          const position = annotation.position_data!;
          const rects = position.kind === "area" ? [position.rect] : position.rects;
          return rects.map((rect, index) => {
            const colors = colorMap[annotation.color ?? "yellow"];
            const isArea = annotation.type === "area";
            return (
              <button
                key={`${annotation.id}-${index}`}
                type="button"
                className={`absolute pointer-events-auto rounded-sm transition-shadow ${activeAnnotationId === annotation.id ? "ring-2 ring-primary-500 ring-offset-1" : ""}`}
                style={{
                  left: `${rect.x * 100}%`,
                  top: `${rect.y * 100}%`,
                  width: `${rect.width * 100}%`,
                  height: `${rect.height * 100}%`,
                  backgroundColor: isArea ? colors.area : annotation.type === "underline" ? "transparent" : colors.highlight,
                  border: isArea ? `2px solid ${colors.underline}` : undefined,
                  borderBottom: annotation.type === "underline" ? `2px solid ${colors.underline}` : undefined,
                }}
                onClick={() => onClick?.(annotation)}
                aria-label={annotation.selected_text ?? "区域标注"}
              />
            );
          });
        })}
    </div>
  );
}
