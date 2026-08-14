import { useState, useRef, useCallback } from "react";
import type { AxiosError } from "axios";
import { Upload, X, FileText, CheckCircle, AlertCircle } from "lucide-react";
import clsx from "clsx";
import { useUploadPaper } from "@/features/paper/hooks";
import { MAX_PDF_SIZE_MB, parseDocument } from "@/features/paper/api";

interface ImportModalProps {
  onClose: () => void;
}

type UploadState = "idle" | "selected" | "uploading" | "success" | "error";

interface FileEntry {
  file: File;
  state: UploadState;
  progress: number;
  error?: string;
}

export function ImportModal({ onClose }: ImportModalProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [entries, setEntries] = useState<FileEntry[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const uploadMut = useUploadPaper();

  const validateFile = (file: File): string | null => {
    // Front-end pre-validation (server still validates)
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      return "不是 PDF 文件";
    }
    if (file.type && file.type !== "application/pdf" && !file.type.includes("pdf")) {
      return "文件类型不是 application/pdf";
    }
    if (file.size > MAX_PDF_SIZE_MB * 1024 * 1024) {
      return `文件超过 ${MAX_PDF_SIZE_MB} MB`;
    }
    return null;
  };

  const handleFiles = useCallback((fileList: FileList | null) => {
    if (!fileList || fileList.length === 0) return;

    const newEntries: FileEntry[] = [];
    for (const file of Array.from(fileList)) {
      const error = validateFile(file);
      newEntries.push({
        file,
        state: error ? "error" : "selected",
        progress: 0,
        error: error ?? undefined,
      });
    }
    setEntries((prev) => [...prev, ...newEntries]);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
      handleFiles(e.dataTransfer.files);
    },
    [handleFiles]
  );

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const uploadOne = async (index: number) => {
    const entry = entries[index];
    if (!entry || entry.state !== "selected") return;

    setEntries((prev) =>
      prev.map((e, i) => (i === index ? { ...e, state: "uploading" } : e))
    );

    try {
      const paper = await uploadMut.mutateAsync({
        file: entry.file,
        onProgress: (progress) => {
          setEntries((prev) =>
            prev.map((e, i) =>
              i === index ? { ...e, progress } : e
            )
          );
        },
      });
      const documentId = paper.document?.id ?? paper.documents[0]?.id;
      if (documentId) void parseDocument(documentId).catch(() => undefined);
      setEntries((prev) =>
        prev.map((e, i) =>
          i === index ? { ...e, state: "success", progress: 100 } : e
        )
      );
    } catch (err: unknown) {
      const axiosError = err as AxiosError<{ detail?: string }>;
      const detail = axiosError.response?.data?.detail || axiosError.message || "上传失败";
      setEntries((prev) =>
        prev.map((e, i) =>
          i === index ? { ...e, state: "error", error: detail } : e
        )
      );
    }
  };

  const handleUploadAll = () => {
    entries.forEach((_, i) => {
      if (entries[i].state === "selected") {
        uploadOne(i);
      }
    });
  };

  const handleRemove = (index: number) => {
    setEntries((prev) => prev.filter((_, i) => i !== index));
  };

  const hasPending = entries.some((e) => e.state === "selected");
  const allDone = entries.length > 0 && entries.every((e) => e.state === "success" || e.state === "error");
  const successCount = entries.filter((e) => e.state === "success").length;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/30"
      onClick={onClose}
    >
      <div
        className="w-full max-w-lg rounded-xl bg-white p-6 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold">导入论文</h2>
          <button
            onClick={onClose}
            className="rounded-lg p-1 text-gray-400 hover:bg-gray-100"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Drop zone */}
        <div
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onClick={() => fileInputRef.current?.click()}
          className={clsx(
            "flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed py-10 transition-colors",
            isDragging
              ? "border-primary-500 bg-primary-50"
              : "border-gray-200 hover:border-primary-300 hover:bg-gray-50"
          )}
        >
          <Upload className="mb-2 h-8 w-8 text-gray-400" />
          <p className="text-sm text-gray-600">拖拽 PDF 到这里</p>
          <p className="mt-1 text-xs text-gray-400">或点击选择文件</p>
          <p className="mt-2 text-xs text-gray-400">PDF · 最大 {MAX_PDF_SIZE_MB} MB</p>
        </div>

        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,application/pdf"
          multiple
          className="hidden"
          onChange={(e) => {
            handleFiles(e.target.files);
            e.target.value = "";
          }}
        />

        {/* File list */}
        {entries.length > 0 && (
          <div className="mt-4 max-h-60 space-y-2 overflow-y-auto">
            {entries.map((entry, i) => (
              <div
                key={i}
                className="flex items-center gap-3 rounded-lg border border-gray-100 p-2"
              >
                {/* Status icon */}
                <div className="shrink-0">
                  {entry.state === "success" ? (
                    <CheckCircle className="h-5 w-5 text-green-500" />
                  ) : entry.state === "error" ? (
                    <AlertCircle className="h-5 w-5 text-red-500" />
                  ) : (
                    <FileText className="h-5 w-5 text-gray-400" />
                  )}
                </div>

                {/* File info + progress */}
                <div className="flex-1 min-w-0">
                  <p className="truncate text-sm text-gray-700">
                    {entry.file.name}
                  </p>
                  <p className="text-xs text-gray-400">
                    {entry.state === "uploading" && `${entry.progress}%`}
                    {entry.state === "success" && "上传成功"}
                    {entry.state === "error" && entry.error}
                    {entry.state === "selected" && "等待上传"}
                  </p>
                  {entry.state === "uploading" && (
                    <div className="mt-1 h-1 overflow-hidden rounded-full bg-gray-100">
                      <div
                        className="h-full bg-primary-500 transition-all"
                        style={{ width: `${entry.progress}%` }}
                      />
                    </div>
                  )}
                </div>

                {/* Remove button */}
                {(entry.state === "selected" || entry.state === "error") && (
                  <button
                    onClick={() => handleRemove(i)}
                    className="shrink-0 rounded p-1 text-gray-400 hover:bg-gray-100"
                  >
                    <X className="h-4 w-4" />
                  </button>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Summary */}
        {allDone && (
          <p className="mt-3 text-center text-sm text-gray-600">
            完成 {successCount} 篇 / 共 {entries.length} 篇
          </p>
        )}

        {/* Actions */}
        <div className="mt-6 flex justify-end gap-2">
          <button onClick={onClose} className="btn-ghost border border-gray-200">
            {allDone ? "关闭" : "取消"}
          </button>
          {hasPending && (
            <button
              onClick={handleUploadAll}
              disabled={uploadMut.isPending}
              className="btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {uploadMut.isPending ? "上传中..." : `导入 ${entries.filter((e) => e.state === "selected").length} 篇`}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
