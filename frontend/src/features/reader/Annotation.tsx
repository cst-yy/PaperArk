import { Highlighter, Underline, MessageSquare, Trash2 } from "lucide-react";
import type { Annotation } from "./types";

interface AnnotationPanelProps {
  annotations: Annotation[];
  onDelete?: (id: string) => void;
  onJumpTo?: (annotation: Annotation) => void;
}

export function AnnotationPanel({ annotations, onDelete, onJumpTo }: AnnotationPanelProps) {
  const icons = {
    highlight: Highlighter,
    underline: Underline,
    comment: MessageSquare,
  };

  if (annotations.length === 0) {
    return (
      <div className="flex h-full items-center justify-center text-sm text-gray-400">
        No annotations yet
      </div>
    );
  }

  // Group by page
  const grouped = annotations.reduce<Record<number, Annotation[]>>((acc, ann) => {
    if (!acc[ann.page_number]) acc[ann.page_number] = [];
    acc[ann.page_number].push(ann);
    return acc;
  }, {});

  return (
    <div className="space-y-4 overflow-y-auto p-3">
      {Object.entries(grouped).map(([page, items]) => (
        <div key={page}>
          <h4 className="mb-2 text-xs font-medium text-gray-400">
            Page {page}
          </h4>
          <div className="space-y-2">
            {items.map((ann) => {
              const Icon = icons[ann.type] || Highlighter;
              return (
                <div
                  key={ann.id}
                  className="group rounded-lg border border-gray-100 p-2 hover:border-gray-200 cursor-pointer"
                  onClick={() => onJumpTo?.(ann)}
                >
                  <div className="flex items-start gap-2">
                    <Icon className="mt-0.5 h-3.5 w-3.5 shrink-0 text-gray-400" />
                    <div className="flex-1 min-w-0">
                      {ann.selected_text && (
                        <p className="text-xs text-gray-600 line-clamp-2">
                          {ann.selected_text}
                        </p>
                      )}
                      {ann.content && (
                        <p className="mt-1 text-xs text-gray-800">{ann.content}</p>
                      )}
                    </div>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onDelete?.(ann.id);
                      }}
                      className="opacity-0 group-hover:opacity-100 transition-opacity"
                    >
                      <Trash2 className="h-3.5 w-3.5 text-gray-400 hover:text-red-500" />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}
