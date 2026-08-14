import { Children, isValidElement, type ReactNode, useState } from "react";
import { AlertCircle, ExternalLink, FileText, Languages, Loader2, RotateCcw, Send } from "lucide-react";
import ReactMarkdown from "react-markdown";
import rehypeKatex from "rehype-katex";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import "katex/dist/katex.min.css";

import { askPaperQuestion } from "./api";
import { DeepReadingPanel } from "./DeepReadingPanel";
import type { AICitation, PaperQAResponse, TranslationResult } from "./types";

interface AIPanelProps {
  paperId: string;
  translationText: string | null;
  translationResult: TranslationResult | null;
  translationPending: boolean;
  translationError: string | null;
  onRetryTranslation: () => void;
  onOpenCitation: (citation: AICitation) => void;
}

export function AIPanel(props: AIPanelProps) {
  const [query, setQuery] = useState("");
  const [answer, setAnswer] = useState<PaperQAResponse | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async () => {
    const normalized = query.trim();
    if (!normalized || pending) return;
    setPending(true);
    setError(null);
    try {
      setAnswer(await askPaperQuestion({ paperId: props.paperId, query: normalized }));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "AI 服务暂时不可用，请稍后重试。");
    } finally {
      setPending(false);
    }
  };

  return <div className="min-h-0 flex-1 overflow-y-auto p-3">
    <section>
      <h3 className="text-sm font-medium text-gray-900 dark:text-gray-100">论文问答</h3>
      <p className="mt-1 text-xs leading-5 text-gray-400">仅依据当前论文原文及其关联笔记回答，不保存问答历史。</p>
      <textarea value={query} maxLength={2000} onChange={(event) => setQuery(event.target.value)} onKeyDown={(event) => { if ((event.ctrlKey || event.metaKey) && event.key === "Enter") void submit(); }} className="mt-3 min-h-24 w-full resize-y rounded-lg border border-gray-200 bg-transparent p-2.5 text-sm outline-none focus:border-primary-400 dark:border-slate-700" placeholder="这篇论文解决了什么问题？" />
      <div className="mt-2 flex items-center justify-between"><span className="text-[11px] text-gray-400">{query.length}/2000 · Ctrl/⌘ Enter</span><button type="button" className="btn-primary px-3 py-1.5 text-xs" disabled={!query.trim() || pending} onClick={() => void submit()}>{pending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Send className="h-3.5 w-3.5" />}提问</button></div>
      {error && <InlineError message={error} />}
      {answer && <div className="mt-4 border-t border-gray-100 pt-4 dark:border-slate-700">
        {answer.insufficient_evidence && <div className="mb-3 rounded-md bg-amber-50 p-2 text-xs leading-5 text-amber-800 dark:bg-amber-950/30 dark:text-amber-200">当前论文的已解析内容中没有找到足够证据支持完整回答。</div>}
        <CitationMarkdown answer={answer.answer} citations={answer.citations} onOpen={props.onOpenCitation} />
        {answer.citations.length > 0 && <div className="mt-4"><p className="mb-2 text-xs font-medium text-gray-500">引用</p><div className="space-y-2">{answer.citations.map((citation) => <CitationCard key={citation.source_key} citation={citation} onOpen={props.onOpenCitation} />)}</div></div>}
      </div>}
    </section>

    {props.translationText && <section className="mt-5 border-t border-gray-100 pt-4 dark:border-slate-700">
      <div className="flex items-center gap-1.5 text-sm font-medium"><Languages className="h-4 w-4" />当前选区翻译</div>
      <blockquote className="mt-2 line-clamp-5 border-l-2 border-gray-200 pl-2 text-xs leading-5 text-gray-500 dark:border-slate-700">{props.translationText}</blockquote>
      {props.translationPending && <div className="mt-3 flex items-center gap-2 text-xs text-gray-400"><Loader2 className="h-4 w-4 animate-spin" />正在翻译…</div>}
      {props.translationError && <div className="mt-3"><InlineError message={props.translationError} /><button type="button" onClick={props.onRetryTranslation} className="mt-2 inline-flex items-center gap-1 text-xs text-primary-600"><RotateCcw className="h-3.5 w-3.5" />重试</button></div>}
      {props.translationResult && <div className="mt-3 whitespace-pre-wrap rounded-lg bg-gray-50 p-3 text-sm leading-6 text-gray-800 dark:bg-slate-800 dark:text-gray-100">{props.translationResult.translated_text}</div>}
    </section>}
    <DeepReadingPanel paperId={props.paperId} onOpenCitation={props.onOpenCitation} />
  </div>;
}

function CitationMarkdown({ answer, citations, onOpen }: { answer: string; citations: AICitation[]; onOpen: (citation: AICitation) => void }) {
  const byLabel = new Map(citations.map((citation) => [citation.label, citation]));
  const replaceMarkers = (children: ReactNode): ReactNode => Children.map(children, (child) => {
    if (typeof child !== "string") return isValidElement(child) ? child : child;
    return child.split(/(\[S\d+\])/g).map((part, index) => {
      const match = /^\[(S\d+)\]$/.exec(part);
      const citation = match ? byLabel.get(match[1]) : undefined;
      return citation ? <button type="button" key={`${citation.label}-${index}`} onClick={() => onOpen(citation)} className="mx-0.5 inline-flex rounded bg-primary-50 px-1 py-0.5 align-baseline text-[11px] font-medium text-primary-700 hover:bg-primary-100 dark:bg-primary-950/40 dark:text-primary-200">[{citation.label}]</button> : part;
    });
  });
  const components = {
    p: ({ children }: { children?: ReactNode }) => <p>{replaceMarkers(children)}</p>,
    li: ({ children }: { children?: ReactNode }) => <li>{replaceMarkers(children)}</li>,
  };
  return <div className="prose prose-sm max-w-none text-sm leading-6 dark:prose-invert"><ReactMarkdown remarkPlugins={[remarkGfm, remarkMath]} rehypePlugins={[rehypeKatex]} components={components}>{answer}</ReactMarkdown></div>;
}

function CitationCard({ citation, onOpen }: { citation: AICitation; onOpen: (citation: AICitation) => void }) {
  const pages = citation.page_start ? citation.page_end && citation.page_end !== citation.page_start ? `p.${citation.page_start}–${citation.page_end}` : `p.${citation.page_start}` : null;
  return <button type="button" onClick={() => onOpen(citation)} className="flex w-full items-start gap-2 rounded-lg border border-gray-200 p-2 text-left hover:border-primary-300 hover:bg-primary-50/40 dark:border-slate-700 dark:hover:bg-slate-800">
    {citation.source_type === "note" ? <FileText className="mt-0.5 h-3.5 w-3.5 shrink-0 text-purple-500" /> : <ExternalLink className="mt-0.5 h-3.5 w-3.5 shrink-0 text-primary-500" />}
    <span className="min-w-0"><span className="block text-[11px] font-medium text-primary-600">[{citation.label}] {citation.source_type === "note" ? "用户笔记" : "论文原文"}</span><span className="block truncate text-xs text-gray-700 dark:text-gray-200">{citation.section_title || citation.title}</span>{pages && <span className="text-[11px] text-gray-400">{pages}</span>}</span>
  </button>;
}

function InlineError({ message }: { message: string }) { return <div className="mt-3 flex gap-2 rounded-md bg-red-50 p-2 text-xs text-red-700 dark:bg-red-950/30 dark:text-red-200"><AlertCircle className="h-4 w-4 shrink-0" />{message}</div>; }
