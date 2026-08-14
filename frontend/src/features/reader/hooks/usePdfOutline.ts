import { useEffect, useState } from "react";
import type { PDFDocumentProxy } from "pdfjs-dist";

import type { OutlineNode } from "../readerTypes";

type PdfOutlineItem = NonNullable<Awaited<ReturnType<PDFDocumentProxy["getOutline"]>>>[number];
type ExplicitDestination = Awaited<ReturnType<PDFDocumentProxy["getDestination"]>>;

async function resolveOutlinePage(
  pdf: PDFDocumentProxy,
  destination: PdfOutlineItem["dest"],
): Promise<number | null> {
  const explicitDestination: ExplicitDestination = typeof destination === "string"
    ? await pdf.getDestination(destination)
    : destination;

  if (!explicitDestination?.[0]) return null;

  try {
    const pageIndex = await pdf.getPageIndex(
      explicitDestination[0] as Parameters<PDFDocumentProxy["getPageIndex"]>[0],
    );
    return pageIndex + 1;
  } catch {
    return null;
  }
}

async function toOutlineNodes(
  pdf: PDFDocumentProxy,
  items: PdfOutlineItem[],
  path = "outline",
): Promise<OutlineNode[]> {
  return Promise.all(
    items.map(async (item, index) => ({
      id: `${path}-${index}`,
      title: item.title?.trim() || "未命名章节",
      pageNumber: await resolveOutlinePage(pdf, item.dest),
      children: await toOutlineNodes(pdf, item.items, `${path}-${index}`),
    })),
  );
}

export function usePdfOutline(pdf: PDFDocumentProxy | null) {
  const [result, setResult] = useState<{ pdf: PDFDocumentProxy | null; outline: OutlineNode[]; isLoading: boolean }>({
    pdf: null,
    outline: [],
    isLoading: false,
  });

  useEffect(() => {
    if (!pdf) return;

    let cancelled = false;
    void pdf.getOutline()
      .then((items) => (items ? toOutlineNodes(pdf, items) : []))
      .then((outline) => {
        if (!cancelled) setResult({ pdf, outline, isLoading: false });
      })
      .catch(() => {
        if (!cancelled) setResult({ pdf, outline: [], isLoading: false });
      });

    return () => {
      cancelled = true;
    };
  }, [pdf]);

  return {
    outline: result.pdf === pdf ? result.outline : [],
    isLoading: pdf !== null && (result.pdf !== pdf || result.isLoading),
  };
}
