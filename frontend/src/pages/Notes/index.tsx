import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import "katex/dist/katex.min.css";
import { FileText } from "lucide-react";
import clsx from "clsx";

interface NoteItem {
  id: string;
  paperId: string;
  title: string;
  excerpt: string;
  updatedAt: string;
}

// Mock data for P0 scaffold
const mockNotes: NoteItem[] = [
  {
    id: "1",
    paperId: "abc",
    title: "FedLDR Notes",
    excerpt: "Label distribution heterogeneity is the core challenge...",
    updatedAt: "2026-08-13",
  },
];

export default function Notes() {
  const [selectedNote, setSelectedNote] = useState<NoteItem | null>(null);
  const [content, setContent] = useState("");

  return (
    <div className="flex h-full">
      {/* Notes list */}
      <div className="w-64 border-r border-gray-200 bg-white">
        <div className="border-b border-gray-100 px-4 py-3">
          <h2 className="text-sm font-semibold">Notes</h2>
        </div>
        <div className="space-y-1 p-2">
          {mockNotes.map((note) => (
            <button
              key={note.id}
              onClick={() => {
                setSelectedNote(note);
                setContent(`# ${note.title}\n\n${note.excerpt}`);
              }}
              className={clsx(
                "w-full rounded-lg p-3 text-left transition-colors",
                selectedNote?.id === note.id
                  ? "bg-primary-50"
                  : "hover:bg-gray-50"
              )}
            >
              <p className="text-sm font-medium line-clamp-1">{note.title}</p>
              <p className="mt-1 text-xs text-gray-500 line-clamp-2">{note.excerpt}</p>
              <p className="mt-1 text-[10px] text-gray-400">{note.updatedAt}</p>
            </button>
          ))}
          {mockNotes.length === 0 && (
            <div className="py-8 text-center text-sm text-gray-400">
              No notes yet
            </div>
          )}
        </div>
      </div>

      {/* Editor */}
      <div className="flex flex-1 flex-col">
        {selectedNote ? (
          <>
            <div className="border-b border-gray-200 px-6 py-3">
              <h1 className="text-base font-semibold">{selectedNote.title}</h1>
            </div>
            <div className="grid flex-1 grid-cols-2 overflow-hidden">
              {/* Markdown editor */}
              <textarea
                value={content}
                onChange={(e) => setContent(e.target.value)}
                className="border-r border-gray-200 p-4 font-mono text-sm outline-none resize-none"
                placeholder="Write your notes in Markdown..."
              />
              {/* Preview */}
              <div className="overflow-y-auto p-4 prose prose-sm max-w-none">
                <ReactMarkdown
                  remarkPlugins={[remarkGfm, remarkMath]}
                  rehypePlugins={[rehypeKatex]}
                >
                  {content}
                </ReactMarkdown>
              </div>
            </div>
          </>
        ) : (
          <div className="flex h-full flex-col items-center justify-center text-gray-400">
            <FileText className="mb-3 h-10 w-10" />
            <p className="text-sm">Select a note or create a new one</p>
          </div>
        )}
      </div>
    </div>
  );
}
