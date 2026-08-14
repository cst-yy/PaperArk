import { pdfjs } from "react-pdf";

// Keep the worker version coupled to the pdfjs-dist version bundled by react-pdf.
pdfjs.GlobalWorkerOptions.workerSrc = new URL(
  "pdfjs-dist/build/pdf.worker.min.mjs",
  import.meta.url,
).toString();
