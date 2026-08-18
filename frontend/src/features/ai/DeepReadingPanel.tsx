import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, Clock3, Loader2, Sparkles, Trash2 } from "lucide-react";
import { useNavigate } from "react-router-dom";

import { createNote } from "@/features/notes/api";
import { useNotes } from "@/features/notes/hooks";
import { getResearchProfile } from "@/features/notes/researchApi";
import {
  applyAIAnalysis, deleteAIAnalysis, generateDeepReading, getAIAnalysis, listAIAnalyses,
} from "./api";
import type {
  AICitation, AIApplicableScalar, DeepReadingContribution, DeepReadingDraft,
  DeepReadingExperiment, GroundedStructuredField,
} from "./types";

const FIELDS = [
  ["background", "研究背景"], ["prior_work_limitations", "前人工作局限"],
  ["research_problem", "研究问题"], ["method_summary", "方法概述"],
  ["results_summary", "结果总结"], ["conclusion", "结论"],
  ["limitations", "局限"], ["future_work", "未来工作"],
] as const;

const historyKey = (paperId: string) => ["papers", paperId, "ai-analyses"] as const;

export function DeepReadingPanel({ paperId, onOpenCitation }: { paperId: string; onOpenCitation: (citation: AICitation) => void }) {
  const client = useQueryClient();
  const history = useQuery({ queryKey: historyKey(paperId), queryFn: () => listAIAnalyses(paperId) });
  const [draft, setDraft] = useState<DeepReadingDraft | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const generate = async () => {
    setPending(true); setError(null);
    try {
      const value = await generateDeepReading(paperId);
      setDraft(value);
      await client.invalidateQueries({ queryKey: historyKey(paperId) });
    } catch (reason) { setError(errorMessage(reason, "结构化分析暂时不可用。")); }
    finally { setPending(false); }
  };

  const openHistory = async (analysisId: string) => {
    setPending(true); setError(null);
    try { setDraft((await getAIAnalysis(analysisId)).draft); }
    catch (reason) { setError(errorMessage(reason, "历史分析读取失败。")); }
    finally { setPending(false); }
  };

  const removeHistory = async (analysisId: string) => {
    if (!window.confirm("删除这条 AI 分析历史？已应用到笔记的内容不会被删除。")) return;
    try {
      await deleteAIAnalysis(analysisId);
      if (draft?.analysis_id === analysisId) setDraft(null);
      await client.invalidateQueries({ queryKey: historyKey(paperId) });
    } catch (reason) { setError(errorMessage(reason, "删除历史分析失败。")); }
  };

  return <section className="mt-5 border-t border-gray-100 pt-4 dark:border-slate-700">
    <div className="flex items-center justify-between gap-2">
      <div className="flex items-center gap-1.5 text-sm font-medium"><Sparkles className="h-4 w-4" />深度阅读</div>
      <button type="button" className="text-xs text-primary-600" disabled={pending} onClick={() => void generate()}>
        {draft ? "重新生成" : "生成分析"}
      </button>
    </div>
    <p className="mt-1 text-xs leading-5 text-gray-400">结果会保存为可追溯的只读分析；只有确认应用才会修改研究笔记。</p>
    {pending && <p className="mt-2 flex items-center gap-1 text-xs text-gray-500"><Loader2 className="h-3.5 w-3.5 animate-spin" />处理中…</p>}
    {error && <p className="mt-2 text-xs text-red-500">{error}</p>}

    {(history.data?.length ?? 0) > 0 && <div className="mt-3 rounded-lg border border-gray-200 p-2 dark:border-slate-700">
      <p className="mb-1.5 flex items-center gap-1 text-xs font-medium"><Clock3 className="h-3.5 w-3.5" />分析历史</p>
      <div className="max-h-28 space-y-1 overflow-auto">{history.data?.map((item) => <div key={item.analysis_id} className="flex items-center gap-1 text-[11px]">
        <button className="min-w-0 flex-1 truncate text-left text-primary-600" onClick={() => void openHistory(item.analysis_id)}>
          {new Date(item.created_at).toLocaleString()} · {item.model} · {item.source_count} sources
        </button>
        <span className="text-gray-400">已应用 {item.application_count}</span>
        <button title="删除分析历史" onClick={() => void removeHistory(item.analysis_id)}><Trash2 className="h-3 w-3 text-red-500" /></button>
      </div>)}</div>
    </div>}

    {!draft && !pending && <button type="button" className="btn-primary mt-3 px-3 py-1.5 text-xs" onClick={() => void generate()}><Sparkles className="h-3.5 w-3.5" />生成深度阅读</button>}
    {draft && <DraftReview key={draft.analysis_id ?? "ephemeral"} draft={draft} paperId={paperId} onOpenCitation={onOpenCitation} onApplied={() => client.invalidateQueries({ queryKey: historyKey(paperId) })} />}
  </section>;
}

function DraftReview({ draft, paperId, onOpenCitation, onApplied }: { draft: DeepReadingDraft; paperId: string; onOpenCitation: (citation: AICitation) => void; onApplied: () => void }) {
  const navigate = useNavigate();
  const notes = useNotes(paperId);
  const researchNotes = notes.data?.filter((note) => note.note_type === "research") ?? [];
  const eligibleScalars = FIELDS.filter(([key]) => draft[key].grounded && !draft[key].insufficient_evidence).map(([key]) => key);
  const eligibleContributions = draft.contributions.filter(isGrounded).map((item) => item.client_id);
  const eligibleExperiments = draft.experiments.filter(isGrounded).map((item) => item.client_id);
  const [scalars, setScalars] = useState<AIApplicableScalar[]>(eligibleScalars);
  const [contributions, setContributions] = useState<string[]>(eligibleContributions);
  const [experiments, setExperiments] = useState<string[]>(eligibleExperiments);
  const [destination, setDestination] = useState("new");
  const [overwrite, setOverwrite] = useState(false);
  const [collectionMode, setCollectionMode] = useState<"append" | "replace">("append");
  const [applying, setApplying] = useState(false);
  const [applyError, setApplyError] = useState<string | null>(null);
  const sourceMap = new Map(draft.sources.map((source) => [source.label, source]));

  const missingDependencies = draft.experiments.filter((item) => experiments.includes(item.client_id))
    .flatMap((item) => item.supports_contribution_client_ids.filter((id) => !contributions.includes(id)));

  const apply = async () => {
    if (!draft.analysis_id || applying || missingDependencies.length > 0) return;
    setApplying(true); setApplyError(null);
    try {
      const note = destination === "new"
        ? await createNote({ paper_id: paperId, note_type: "research", title: "AI 深度阅读草稿", content_markdown: "" })
        : researchNotes.find((item) => item.id === destination);
      if (!note) throw new Error("请选择有效的研究笔记。");
      const current = await getResearchProfile(note.id);
      await applyAIAnalysis(draft.analysis_id, {
        note_id: note.id,
        apply: { scalar_fields: scalars, contribution_client_ids: contributions, experiment_client_ids: experiments },
        scalar_conflict_policy: overwrite ? "replace" : "fill_empty",
        collections_mode: collectionMode,
        expected_revision: current?.revision ?? 0,
      });
      onApplied();
      navigate(`/notes/${note.id}?view=structured`);
    } catch (reason) { setApplyError(errorMessage(reason, "应用失败，请刷新目标笔记后重试。")); }
    finally { setApplying(false); }
  };

  return <div className="mt-3">
    <div className="rounded-lg bg-gray-50 p-2 text-[11px] text-gray-500 dark:bg-slate-800">
      <p>{draft.provider_name ?? "unknown"} / {draft.model ?? "unknown"} · prompt {draft.prompt_version ?? "unknown"}</p>
      <p className="truncate" title={draft.source_snapshot_hash ?? ""}>来源快照 {draft.source_snapshot_hash?.slice(0, 12) ?? "未持久化"} · {draft.source_count} sources</p>
    </div>
    <div className="mt-3 space-y-2">{FIELDS.map(([key, label]) => <Selectable key={key} checked={scalars.includes(key)} disabled={!isGrounded(draft[key])} onChange={() => setScalars(toggle(scalars, key))}>
      <FieldCard label={label} field={draft[key]} sourceMap={sourceMap} onOpen={onOpenCitation} />
    </Selectable>)}</div>
    {draft.contributions.length > 0 && <div className="mt-4"><p className="mb-2 text-xs font-medium">创新点</p>{draft.contributions.map((item, index) => <Selectable key={item.client_id} checked={contributions.includes(item.client_id)} disabled={!isGrounded(item)} onChange={() => setContributions(toggle(contributions, item.client_id))}><ContributionCard item={item} index={index} sourceMap={sourceMap} onOpen={onOpenCitation} /></Selectable>)}</div>}
    {draft.experiments.length > 0 && <div className="mt-4"><p className="mb-2 text-xs font-medium">实验</p>{draft.experiments.map((item, index) => <Selectable key={item.client_id} checked={experiments.includes(item.client_id)} disabled={!isGrounded(item)} onChange={() => setExperiments(toggle(experiments, item.client_id))}><ExperimentCard item={item} index={index} sourceMap={sourceMap} onOpen={onOpenCitation} /></Selectable>)}</div>}
    <div className="mt-5 rounded-lg border border-gray-200 p-3 dark:border-slate-700"><p className="text-xs font-medium">确认应用到研究笔记</p>
      <select className="input mt-2 py-1.5 text-xs" value={destination} onChange={(event) => setDestination(event.target.value)}><option value="new">新建 Research Note</option>{researchNotes.map((note) => <option key={note.id} value={note.id}>{note.title}</option>)}</select>
      <label className="mt-2 flex items-start gap-2 text-xs"><input type="checkbox" checked={overwrite} onChange={(event) => setOverwrite(event.target.checked)} />覆盖已存在的标量字段（默认只填空字段）</label>
      <label className="mt-2 block text-xs">创新点与实验：<select className="ml-1 rounded border bg-transparent px-1 py-0.5" value={collectionMode} onChange={(event) => setCollectionMode(event.target.value as "append" | "replace")}><option value="append">追加所选卡片</option><option value="replace">用所选卡片替换</option></select></label>
      <p className="mt-2 text-[11px] leading-4 text-gray-400">“我的思考”受服务端保护。来源不会自动创建 Annotation 或 NoteEvidence；点击来源后请回原文人工确认与标注。</p>
      {missingDependencies.length > 0 && <p className="mt-2 text-xs text-amber-600">所选实验依赖未选择的创新点：{[...new Set(missingDependencies)].join(", ")}</p>}
      <button type="button" className="btn-primary mt-3 w-full justify-center px-3 py-1.5 text-xs" disabled={applying || !draft.analysis_id || missingDependencies.length > 0} onClick={() => void apply()}>{applying ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <CheckCircle2 className="h-3.5 w-3.5" />}确认并应用所选内容</button>
      {!draft.analysis_id && <p className="mt-2 text-xs text-amber-600">该结果未形成持久化分析，不能应用。</p>}
      {applyError && <p className="mt-2 text-xs text-red-500">{applyError}</p>}
    </div>
  </div>;
}

function Selectable({ checked, disabled, onChange, children }: { checked: boolean; disabled: boolean; onChange: () => void; children: React.ReactNode }) { return <div className={`relative pl-6 ${disabled ? "opacity-60" : ""}`}><input className="absolute left-0 top-3" type="checkbox" checked={checked} disabled={disabled} onChange={onChange} />{children}</div>; }
function SourceChips({ refs, sourceMap, onOpen }: { refs: string[]; sourceMap: Map<string, AICitation>; onOpen: (citation: AICitation) => void }) { return <div className="mt-2 flex flex-wrap gap-1">{refs.map((ref) => { const source = sourceMap.get(ref); return source ? <button key={ref} type="button" title="查看原文并人工确认；不会自动创建证据" className="rounded bg-primary-50 px-1.5 py-0.5 text-[10px] text-primary-700" onClick={() => onOpen(source)}>[{ref}] {source.page_start ? `p.${source.page_start}` : source.section_title || "查看原文"}</button> : null; })}</div>; }
function FieldCard({ label, field, sourceMap, onOpen }: { label: string; field: GroundedStructuredField; sourceMap: Map<string, AICitation>; onOpen: (citation: AICitation) => void }) { return <article className="rounded-lg border border-gray-200 p-2.5 dark:border-slate-700"><div className="flex justify-between"><h4 className="text-xs font-medium">{label}</h4><span className={`text-[10px] ${isGrounded(field) ? "text-green-600" : "text-amber-600"}`}>{isGrounded(field) ? "Grounded" : "证据不足"}</span></div><p className="mt-1 whitespace-pre-wrap text-xs leading-5 text-gray-600 dark:text-gray-300">{field.content || "未找到足够证据"}</p><SourceChips refs={field.evidence_refs} sourceMap={sourceMap} onOpen={onOpen} /></article>; }
function ContributionCard({ item, index, sourceMap, onOpen }: { item: DeepReadingContribution; index: number; sourceMap: Map<string, AICitation>; onOpen: (citation: AICitation) => void }) { return <article className="mb-2 rounded-lg bg-gray-50 p-2.5 text-xs dark:bg-slate-800"><p className="font-medium">创新点 {index + 1}</p><p className="mt-1"><b>问题：</b>{item.problem}</p><p><b>前人局限：</b>{item.prior_limitation}</p><p><b>创新：</b>{item.innovation}</p><p><b>方案：</b>{item.solution}</p><SourceChips refs={item.evidence_refs} sourceMap={sourceMap} onOpen={onOpen} /></article>; }
function ExperimentCard({ item, index, sourceMap, onOpen }: { item: DeepReadingExperiment; index: number; sourceMap: Map<string, AICitation>; onOpen: (citation: AICitation) => void }) { return <article className="mb-2 rounded-lg bg-gray-50 p-2.5 text-xs dark:bg-slate-800"><p className="font-medium">实验 {index + 1}</p><p className="mt-1">{item.task}</p><p className="text-gray-500">{[...item.datasets, ...item.baselines, ...item.metrics].join(" · ")}</p><p className="mt-1">{item.result} {item.conclusion}</p><SourceChips refs={item.evidence_refs} sourceMap={sourceMap} onOpen={onOpen} /></article>; }
function isGrounded(value: { grounded: boolean; insufficient_evidence: boolean }) { return value.grounded && !value.insufficient_evidence; }
function toggle<T>(values: T[], value: T): T[] { return values.includes(value) ? values.filter((item) => item !== value) : [...values, value]; }
function errorMessage(reason: unknown, fallback: string): string { const detail = (reason as { response?: { data?: { detail?: string } } })?.response?.data?.detail; return detail || (reason instanceof Error ? reason.message : fallback); }
