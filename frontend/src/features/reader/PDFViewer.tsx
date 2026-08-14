import { useRef, useState } from "react";

interface PDFViewerProps {
  pdfUrl: string;
  pageNumber: number;
  onPageChange: (page: number) => void;
  onTextSelect?: (text: string, page: number) => void;
}

export function PDFViewer({ pdfUrl, pageNumber, onPageChange, onTextSelect }: PDFViewerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [numPages] = useState<number>(0);
  const [scale, setScale] = useState(1.0);

  // TODO: Integrate react-pdf in Sprint 4
  // For now, render an iframe as a fallback
  return (
    <div className="flex h-full flex-col">
      {/* Toolbar */}
      <div className="flex items-center justify-between border-b border-gray-200 px-4 py-2">
        <div className="flex items-center gap-2">
          <button
            className="btn-ghost"
            onClick={() => onPageChange(Math.max(1, pageNumber - 1))}
            disabled={pageNumber <= 1}
          >
            Prev
          </button>
          <span className="text-sm text-gray-600">
            Page {pageNumber} / {numPages || "?"}
          </span>
          <button
            className="btn-ghost"
            onClick={() => onPageChange(Math.min(numPages, pageNumber + 1))}
            disabled={numPages > 0 && pageNumber >= numPages}
          >
            Next
          </button>
        </div>
        <div className="flex items-center gap-2">
          <button
            className="btn-ghost"
            onClick={() => setScale((s) => Math.max(0.5, s - 0.1))}
          >
            -
          </button>
          <span className="text-xs text-gray-500">{Math.round(scale * 100)}%</span>
          <button
            className="btn-ghost"
            onClick={() => setScale((s) => Math.min(2.0, s + 0.1))}
          >
            +
          </button>
        </div>
      </div>

      {/* PDF View */}
      <div
        ref={containerRef}
        className="flex-1 overflow-auto bg-gray-100"
        onMouseUp={() => {
          const selection = window.getSelection();
          if (selection && selection.toString().trim() && onTextSelect) {
            onTextSelect(selection.toString(), pageNumber);
          }
        }}
      >
        <iframe
          src={`${pdfUrl}#page=${pageNumber}&zoom=${scale * 100}&toolbar=0`}
          className="h-full w-full border-0"
          title="PDF Viewer"
        />
      </div>
    </div>
  );
}
