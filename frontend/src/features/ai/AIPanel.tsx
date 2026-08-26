import { useEffect, useState } from "react";
import { AlertCircle, Languages, Loader2, RotateCcw, Send } from "lucide-react";
import ReactMarkdown from "react-markdown";
import rehypeKatex from "rehype-katex";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import "katex/dist/katex.min.css";

import { createChatSession, listChatMessages, listChatSessions, saveChatMessageAsNote, sendChatMessage } from "./api";
import { DeepReadingPanel } from "./DeepReadingPanel";
import type { AICitation, AIChatMessage, AIChatSession, TranslationResult } from "./types";

interface Props { paperId:string; pageNumber:number; translationText:string|null; translationResult:TranslationResult|null; translationPending:boolean; translationError:string|null; onRetryTranslation:()=>void; onOpenCitation:(citation:AICitation)=>void; }

export function AIPanel(props:Props){
  const[query,setQuery]=useState(""); const[session,setSession]=useState<AIChatSession|null>(null); const[messages,setMessages]=useState<AIChatMessage[]>([]);
  const[scope,setScope]=useState<"page"|"paper">("page"); const[pending,setPending]=useState(false); const[error,setError]=useState<string|null>(null);
  useEffect(()=>{let active=true;void listChatSessions(props.paperId).then(async rows=>{const selected=rows[0]??await createChatSession(props.paperId,"page");if(!active)return;setSession(selected);const history=await listChatMessages(selected.id);if(active)setMessages(history)}).catch(reason=>active&&setError(reason instanceof Error?reason.message:"无法读取问答会话"));return()=>{active=false}},[props.paperId]);
  const submit=async()=>{const value=query.trim();if(!value||pending)return;setPending(true);setError(null);try{let current=session;if(!current){current=await createChatSession(props.paperId,scope);setSession(current)}const turn=await sendChatMessage(current.id,value,scope,props.pageNumber);setMessages(rows=>[...rows,turn.user_message,turn.assistant_message]);setQuery("")}catch(reason){setError(reason instanceof Error?reason.message:"AI 服务暂时不可用，请稍后重试")}finally{setPending(false)}};
  const open=(citation:AIChatMessage["citations"][number])=>props.onOpenCitation({label:`S${citation.citation_order}`,source_key:citation.id,source_type:"paper_chunk",paper_id:citation.paper_id,title:"论文原文",page_start:citation.page_number??undefined,page_end:citation.page_number??undefined});
  return <div className="min-h-0 flex-1 overflow-y-auto p-3">
    <section><div className="flex items-center justify-between"><h3 className="text-sm font-medium">论文问答</h3><button className="text-[11px] text-primary-600" onClick={()=>void createChatSession(props.paperId,scope).then(value=>{setSession(value);setMessages([])})}>新建会话</button></div>
      <div className="mt-2 flex items-center justify-between gap-2"><p className="truncate text-xs text-gray-400">回答范围：当前论文 · {scope==="page"?`第 ${props.pageNumber} 页`:"整篇论文"}</p><select className="rounded border border-gray-200 bg-transparent px-1.5 py-1 text-xs dark:border-slate-700" value={scope} onChange={e=>setScope(e.target.value as "page"|"paper")}><option value="page">当前页</option><option value="paper">整篇论文</option></select></div>
      {messages.length>0&&<div className="mt-3 space-y-3">{messages.map(message=><div key={message.id} className={message.role==="user"?"ml-6 rounded-lg bg-primary-50 p-2 text-sm dark:bg-primary-950/30":"rounded-lg bg-gray-50 p-3 text-sm dark:bg-slate-800"}>{message.role==="assistant"?<><div className="prose prose-sm max-w-none dark:prose-invert"><ReactMarkdown remarkPlugins={[remarkGfm,remarkMath]} rehypePlugins={[rehypeKatex]}>{message.content}</ReactMarkdown></div>{message.citations.length>0&&<div className="mt-2 flex flex-wrap gap-1">{message.citations.map(c=><button key={c.id} className="rounded bg-primary-100 px-1.5 py-0.5 text-[11px] text-primary-700" title={c.quote_text} onClick={()=>open(c)}>[{c.citation_order}] p.{c.page_number??"?"}</button>)}</div>}<button className="mt-2 text-[11px] text-primary-600" onClick={()=>void saveChatMessageAsNote(message.id)}>保存为笔记</button></>:message.content}</div>)}</div>}
      <textarea value={query} maxLength={4000} onChange={e=>setQuery(e.target.value)} onKeyDown={e=>{if(e.key==="Enter"&&!e.shiftKey){e.preventDefault();void submit()}}} className="mt-3 min-h-20 w-full resize-y rounded-lg border border-gray-200 bg-transparent p-2.5 text-sm outline-none focus:border-primary-400 dark:border-slate-700" placeholder="依据当前论文提问…"/>
      <div className="mt-2 flex justify-end"><button className="btn-primary px-3 py-1.5 text-xs" disabled={!query.trim()||pending} onClick={()=>void submit()}>{pending?<Loader2 className="h-3.5 w-3.5 animate-spin"/>:<Send className="h-3.5 w-3.5"/>}提问</button></div>{error&&<InlineError message={error}/>}</section>
    {props.translationText&&<section className="mt-5 border-t border-gray-100 pt-4 dark:border-slate-700"><div className="flex items-center gap-1.5 text-sm font-medium"><Languages className="h-4 w-4"/>当前选区翻译</div><blockquote className="mt-2 line-clamp-5 border-l-2 pl-2 text-xs text-gray-500">{props.translationText}</blockquote>{props.translationPending&&<p className="mt-2 text-xs text-gray-400">正在翻译…</p>}{props.translationError&&<><InlineError message={props.translationError}/><button className="mt-2 inline-flex items-center gap-1 text-xs text-primary-600" onClick={props.onRetryTranslation}><RotateCcw className="h-3 w-3"/>重试</button></>}{props.translationResult&&<div className="mt-3 whitespace-pre-wrap rounded-lg bg-gray-50 p-3 text-sm dark:bg-slate-800">{props.translationResult.translated_text}</div>}</section>}
    <DeepReadingPanel paperId={props.paperId} onOpenCitation={props.onOpenCitation}/>
  </div>
}
function InlineError({message}:{message:string}){return <div className="mt-3 flex gap-2 rounded-md bg-red-50 p-2 text-xs text-red-700 dark:bg-red-950/30 dark:text-red-200"><AlertCircle className="h-4 w-4 shrink-0"/>{message}</div>}
