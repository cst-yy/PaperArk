import { useEffect, useRef, useState } from "react";
import { FilePlus2, FileText, Loader2, Trash2 } from "lucide-react";
import ReactMarkdown from "react-markdown";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import rehypeKatex from "rehype-katex";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import "katex/dist/katex.min.css";

import { useCreateNote, useDeleteNote, useNote, useNotes, useSaveNote } from "@/features/notes/hooks";
import type { Note } from "@/features/notes/types";
import { NoteEvidencePanel } from "@/features/notes/NoteEvidencePanel";
import { ResearchProfileEditor } from "@/features/notes/ResearchProfileEditor";
import { useResearchProfile } from "@/features/notes/researchHooks";

function NoteEditor({ note }: { note: Note }) {
  const [title, setTitle] = useState(note.title);
  const [content, setContent] = useState(note.content_markdown);
  const [dirty, setDirty] = useState(false);
  const revision = useRef(0);
  const save = useSaveNote(note.id);
  const { mutate: saveAggregate, isPending, isError } = save;

  useEffect(() => {
    if (!dirty || !title.trim() || isPending) return;
    const timer = window.setTimeout(() => {
      const savingRevision = revision.current;
      saveAggregate({ paper_id: note.paper_id, title: title.trim(), content_markdown: content, note_type: note.note_type }, {
        onSuccess: () => {
          if (revision.current === savingRevision) setDirty(false);
        },
      });
    }, 1000);
    return () => window.clearTimeout(timer);
  }, [content, dirty, isPending, note.note_type, note.paper_id, saveAggregate, title]);

  const status = isError ? "保存失败" : isPending ? "正在保存…" : dirty ? "等待保存…" : "已保存";
  return <div className="flex min-w-0 flex-1 flex-col">
    <div className="flex items-center gap-3 border-b border-gray-200 px-5 py-3 dark:border-slate-700">
      <input value={title} maxLength={500} onChange={(event) => { revision.current += 1; setTitle(event.target.value); setDirty(true); }} className="min-w-0 flex-1 bg-transparent text-base font-semibold outline-none" aria-label="笔记标题" />
      <span className={`text-xs ${isError ? "text-red-500" : "text-gray-400"}`}>{status}</span>
    </div>
    <div className="grid min-h-0 flex-1 grid-cols-1 lg:grid-cols-2">
      <textarea value={content} onChange={(event) => { revision.current += 1; setContent(event.target.value); setDirty(true); }} className="min-h-[320px] resize-none border-b border-gray-200 bg-transparent p-5 font-mono text-sm leading-6 outline-none dark:border-slate-700 lg:border-b-0 lg:border-r" placeholder="使用 Markdown 写笔记，支持 $LaTeX$…" aria-label="Markdown 正文" />
      <div className="prose prose-sm max-w-none overflow-y-auto p-5 dark:prose-invert">
        {content ? <ReactMarkdown remarkPlugins={[remarkGfm, remarkMath]} rehypePlugins={[rehypeKatex]}>{content}</ReactMarkdown> : <p className="text-gray-400">预览将在这里显示。原始 HTML 默认不会执行。</p>}
      </div>
    </div>
  </div>;
}

function ResearchView({note}:{note:Note}){const profile=useResearchProfile(note.id);if(profile.isLoading)return <div className="flex flex-1 items-center justify-center"><Loader2 className="h-5 w-5 animate-spin" /></div>;return <ResearchProfileEditor key={profile.data?.updated_at??"empty"} note={note} profile={profile.data??null} />;}

export default function Notes() {
  const { noteId, paperId } = useParams<{ noteId?: string; paperId?: string }>();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const notes = useNotes(paperId);
  const detail = useNote(noteId);
  const create = useCreateNote();
  const remove = useDeleteNote();
  const [mode, setMode] = useState<"body"|"structured">(searchParams.get("view") === "structured" ? "structured" : "body");

  const handleCreate = () => create.mutate({ paper_id: paperId ?? null, note_type: paperId ? "paper" : "general", title: "Untitled note", content_markdown: "" }, {
    onSuccess: (note) => navigate(`/notes/${note.id}`),
  });
  const handleCreateResearch = () => paperId && create.mutate({paper_id:paperId,note_type:"research",title:"Structured research note",content_markdown:""},{onSuccess:(note)=>navigate(`/notes/${note.id}`)});
  const handleDelete = () => {
    if (!noteId || !window.confirm("删除这篇笔记？此操作不会删除关联论文。")) return;
    remove.mutate(noteId, { onSuccess: () => navigate(paperId ? `/papers/${paperId}/notes` : "/notes", { replace: true }) });
  };

  return <div className="flex h-[calc(100vh-4rem)] min-h-0 bg-white dark:bg-slate-900">
    <aside className="flex w-72 shrink-0 flex-col border-r border-gray-200 dark:border-slate-700">
      <div className="flex items-center justify-between border-b border-gray-200 px-4 py-3 dark:border-slate-700">
        <div><h1 className="font-semibold">研究笔记</h1>{paperId && <p className="text-xs text-gray-400">当前论文</p>}</div>
        <div className="flex"><button onClick={handleCreate} disabled={create.isPending} className="rounded-md p-2 text-primary-600 hover:bg-primary-50" title="新建笔记"><FilePlus2 className="h-4 w-4" /></button>{paperId&&<button onClick={handleCreateResearch} className="rounded px-2 text-xs text-primary-600" title="新建结构化研究笔记">研究</button>}</div>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto p-2">
        {notes.isLoading && <Loader2 className="mx-auto mt-8 h-5 w-5 animate-spin text-gray-400" />}
        {notes.data?.map((note) => <button key={note.id} onClick={() => navigate(`/notes/${note.id}`)} className={`mb-1 w-full rounded-lg p-3 text-left ${note.id === noteId ? "bg-primary-50 dark:bg-primary-950/30" : "hover:bg-gray-50 dark:hover:bg-slate-800"}`}>
          <p className="truncate text-sm font-medium">{note.title}</p><p className="mt-1 line-clamp-2 text-xs text-gray-500">{note.content_markdown || "空白笔记"}</p><p className="mt-1 text-[10px] text-gray-400">{new Date(note.updated_at).toLocaleString()}</p>
        </button>)}
        {notes.data?.length === 0 && <p className="py-10 text-center text-sm text-gray-400">暂无笔记</p>}
      </div>
    </aside>
    {noteId && detail.data ? <div className="flex min-w-0 flex-1 flex-col">{detail.data.note_type==="research"&&<div className="flex justify-center gap-1 border-b p-2"><button onClick={()=>setMode("body")} className={mode==="body"?"btn-primary":"btn-ghost"}>笔记正文</button><button onClick={()=>setMode("structured")} className={mode==="structured"?"btn-primary":"btn-ghost"}>结构化阅读</button></div>}<div className="flex min-h-0 flex-1">{mode==="structured"&&detail.data.note_type==="research"?<ResearchView note={detail.data}/>:<NoteEditor key={detail.data.id} note={detail.data}/>}<NoteEvidencePanel note={detail.data}/><button onClick={handleDelete} disabled={remove.isPending} className="m-3 self-start rounded-md p-2 text-red-500 hover:bg-red-50" title="删除笔记"><Trash2 className="h-4 w-4" /></button></div></div> : <div className="flex flex-1 flex-col items-center justify-center text-gray-400"><FileText className="mb-3 h-10 w-10" /><p>选择一篇笔记或新建笔记</p></div>}
  </div>;
}
