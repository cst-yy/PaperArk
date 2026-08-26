import { CalendarDays, CheckSquare2, Ellipsis, Link2, Plus, Trash2 } from "lucide-react";
import { useState } from "react";
import { Popover } from "@/components/overlay";
import { usePapers } from "@/features/paper/hooks";
import { useCreateTodo, useDeleteTodo, useTodos, useUpdateTodo } from "@/features/todos/hooks";
import type { Todo, TodoPriority } from "@/features/todos/types";

const labels: Record<TodoPriority, string> = { low: "低", normal: "普通", high: "高" };

export function TodoWidget() {
  const todos = useTodos();
  const create = useCreateTodo();
  const update = useUpdateTodo();
  const remove = useDeleteTodo();
  const papers = usePapers({ page_size: 100 });
  const [adding, setAdding] = useState(false);
  const [title, setTitle] = useState("");
  const [priority, setPriority] = useState<TodoPriority>("normal");
  const [due, setDue] = useState("");
  const [paperId, setPaperId] = useState("");
  const [menu, setMenu] = useState<string>();
  const [undo, setUndo] = useState<Todo>();

  const add = async () => {
    if (!title.trim()) return;
    try {
      await create.mutateAsync({ title: title.trim(), priority, due_at: due ? new Date(`${due}T23:59:59`).toISOString() : null, related_paper_id: paperId || null });
      setTitle(""); setDue(""); setPaperId(""); setAdding(false);
    } catch { /* preserve draft */ }
  };

  return <section className="card flex min-h-0 flex-col overflow-hidden p-3">
    <header className="mb-1 flex h-6 shrink-0 items-center gap-2">
      <CheckSquare2 className="h-4 w-4 text-emerald-500"/><h2 className="text-sm font-semibold">待办</h2><span className="text-[10px] text-gray-400">{todos.data?.length ?? 0}</span>
      {undo && <button className="ml-auto text-[10px] text-primary-600" onClick={async () => { await update.mutateAsync({ id: undo.id, data: { expected_revision: undo.revision, completed: false } }); setUndo(undefined); }}>已完成 · 撤销</button>}
      <button className={undo ? "rounded p-1 text-gray-400 hover:bg-gray-100" : "ml-auto rounded p-1 text-gray-400 hover:bg-gray-100"} aria-label="新增待办" onClick={() => setAdding((value) => !value)}><Plus className="h-4 w-4"/></button>
    </header>
    {adding && <div className="mb-1 grid shrink-0 grid-cols-[1fr_auto] gap-1 rounded-lg bg-gray-50 p-1.5 dark:bg-slate-800">
      <input autoFocus className="input h-7 min-w-0 text-xs" placeholder="输入待办，Enter 创建" value={title} onChange={(event) => setTitle(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter") void add(); if (event.key === "Escape" && !title) setAdding(false); }}/>
      <button className="btn-primary h-7 px-2 text-xs" disabled={!title.trim() || create.isPending} onClick={() => void add()}>添加</button>
      <select aria-label="待办优先级" className="input h-7 text-[10px]" value={priority} onChange={(event) => setPriority(event.target.value as TodoPriority)}>{Object.entries(labels).map(([value, label]) => <option key={value} value={value}>{label}优先级</option>)}</select>
      <input aria-label="待办截止日期" type="date" className="input h-7 text-[10px]" value={due} onChange={(event) => setDue(event.target.value)}/>
      <select aria-label="关联论文" className="input col-span-2 h-7 text-[10px]" value={paperId} onChange={(event) => setPaperId(event.target.value)}><option value="">不关联论文</option>{papers.data?.items.map((paper) => <option key={paper.id} value={paper.id}>{paper.title}</option>)}</select>
      {create.isError && <p className="col-span-2 text-[10px] text-red-600">创建失败，草稿已保留。</p>}
    </div>}
    <div className="min-h-0 flex-1 overflow-y-auto">
      {todos.isLoading ? <p className="py-4 text-center text-xs text-gray-400">加载待办…</p> : todos.data?.length ? todos.data.map((item) => <TodoRow key={item.id} item={item} papers={papers.data?.items ?? []} menuOpen={menu === item.id} onMenu={(open) => setMenu(open ? item.id : undefined)} onPatch={(data) => update.mutate({ id: item.id, data: { expected_revision: item.revision, ...data } })} onComplete={async () => { const result = await update.mutateAsync({ id: item.id, data: { expected_revision: item.revision, completed: true } }); setUndo(result); }} onDelete={() => remove.mutate(item.id)}/>) : <p className="py-4 text-center text-xs text-gray-400">暂无待办，保持轻盈。</p>}
    </div>
  </section>;
}

function TodoRow({ item, papers, menuOpen, onMenu, onPatch, onComplete, onDelete }: { item: Todo; papers: {id:string;title:string}[]; menuOpen:boolean; onMenu:(open:boolean)=>void; onPatch:(data:Partial<{title:string;priority:TodoPriority;due_at:string|null;related_paper_id:string|null}>)=>void; onComplete:()=>void; onDelete:()=>void }) {
  const overdue = item.due_at && new Date(item.due_at) < new Date();
  return <div className="group flex items-start gap-2 border-t border-gray-100 py-1.5 first:border-0 dark:border-slate-800">
    <input className="mt-0.5" type="checkbox" checked={false} aria-label={`完成待办 ${item.title}`} onChange={() => void onComplete()}/>
    <div className="min-w-0 flex-1"><p className="truncate text-xs font-medium" title={item.title}>{item.title}</p><div className="flex gap-2 text-[10px] text-gray-400">{item.priority !== "normal" && <span className={item.priority === "high" ? "text-amber-600" : ""}>{labels[item.priority]}优先</span>}{item.due_at && <span className={overdue ? "text-red-500" : ""}><CalendarDays className="mr-0.5 inline h-3 w-3"/>{new Date(item.due_at).toLocaleDateString("zh-CN")}</span>}{item.related_paper_title && <span className="truncate"><Link2 className="mr-0.5 inline h-3 w-3"/>{item.related_paper_title}</span>}</div></div>
    <Popover open={menuOpen} onOpenChange={onMenu} trigger={(props) => <button {...props} aria-label={`管理待办 ${item.title}`} className="rounded p-1 text-gray-400 opacity-0 hover:bg-gray-100 group-hover:opacity-100 focus:opacity-100"><Ellipsis className="h-3.5 w-3.5"/></button>} contentClassName="absolute right-0 z-30 mt-1 w-56 space-y-1 rounded-lg border bg-white p-2 shadow-xl dark:border-slate-700 dark:bg-slate-900">
      <input aria-label="编辑待办标题" className="input h-7 text-xs" defaultValue={item.title} onKeyDown={(event) => { if (event.key === "Enter" && event.currentTarget.value.trim()) onPatch({ title: event.currentTarget.value.trim() }); }}/>
      <select aria-label="编辑待办优先级" className="input h-7 text-xs" value={item.priority} onChange={(event) => onPatch({ priority: event.target.value as TodoPriority })}>{Object.entries(labels).map(([value, label]) => <option key={value} value={value}>{label}优先级</option>)}</select>
      <input aria-label="编辑待办截止日期" type="date" className="input h-7 text-xs" value={item.due_at ? item.due_at.slice(0,10) : ""} onChange={(event) => onPatch({ due_at: event.target.value ? new Date(`${event.target.value}T23:59:59`).toISOString() : null })}/>
      <select aria-label="编辑待办关联论文" className="input h-7 text-xs" value={item.related_paper_id ?? ""} onChange={(event) => onPatch({ related_paper_id: event.target.value || null })}><option value="">不关联论文</option>{papers.map((paper) => <option key={paper.id} value={paper.id}>{paper.title}</option>)}</select>
      <button className="flex w-full items-center gap-1 rounded px-2 py-1 text-xs text-red-600 hover:bg-red-50" onClick={onDelete}><Trash2 className="h-3.5 w-3.5"/>删除</button>
    </Popover>
  </div>;
}
