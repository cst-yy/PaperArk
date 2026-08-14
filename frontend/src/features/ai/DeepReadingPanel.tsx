import { useState } from "react";
import { CheckCircle2, Loader2, Sparkles } from "lucide-react";
import { useNavigate } from "react-router-dom";

import { createNote } from "@/features/notes/api";
import { useNotes } from "@/features/notes/hooks";
import { getResearchProfile, saveResearchProfile } from "@/features/notes/researchApi";
import { emptyResearchProfile, type ResearchProfileDraft, type ResearchProfileResponse } from "@/features/notes/researchTypes";
import { generateDeepReading } from "./api";
import type { AICitation, DeepReadingContribution, DeepReadingDraft, DeepReadingExperiment, GroundedStructuredField } from "./types";

const FIELDS = [
  ["background", "研究背景"], ["prior_work_limitations", "前人工作局限"],
  ["research_problem", "研究问题"], ["method_summary", "方法概述"],
  ["results_summary", "结果总结"], ["conclusion", "结论"],
  ["limitations", "局限"], ["future_work", "未来工作"],
] as const;

export function DeepReadingPanel({ paperId, onOpenCitation }: { paperId: string; onOpenCitation: (citation: AICitation) => void }) {
  const navigate = useNavigate();
  const notes = useNotes(paperId);
  const researchNotes = notes.data?.filter((note) => note.note_type === "research") ?? [];
  const [draft, setDraft] = useState<DeepReadingDraft | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [destination, setDestination] = useState("new");
  const [overwrite, setOverwrite] = useState(false);
  const [groundedOnly, setGroundedOnly] = useState(true);
  const [collectionMode, setCollectionMode] = useState<"append" | "replace">("append");
  const [applying, setApplying] = useState(false);
  const [applyError, setApplyError] = useState<string | null>(null);

  const generate = async () => {
    setPending(true); setError(null);
    try { setDraft(await generateDeepReading(paperId)); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "结构化分析暂时不可用。"); }
    finally { setPending(false); }
  };

  const apply = async () => {
    if (!draft || applying) return;
    setApplying(true); setApplyError(null);
    try {
      const note = destination === "new"
        ? await createNote({ paper_id: paperId, note_type: "research", title: "AI 深度阅读草稿", content_markdown: "" })
        : researchNotes.find((item) => item.id === destination);
      if (!note) throw new Error("请选择有效的研究笔记。");
      const current = await getResearchProfile(note.id);
      const aggregate = buildAggregate(current, draft, { overwrite, groundedOnly, collectionMode });
      await saveResearchProfile(note.id, aggregate);
      navigate(`/notes/${note.id}?view=structured`);
    } catch (reason) { setApplyError(reason instanceof Error ? reason.message : "应用失败，请稍后重试。"); }
    finally { setApplying(false); }
  };

  if (!draft) return <section className="mt-5 border-t border-gray-100 pt-4 dark:border-slate-700">
    <div className="flex items-center gap-1.5 text-sm font-medium"><Sparkles className="h-4 w-4" />深度阅读</div>
    <p className="mt-1 text-xs leading-5 text-gray-400">基于论文原文进行多意图结构化分析。生成结果只是临时 Draft，不会修改笔记。</p>
    <button type="button" className="btn-primary mt-3 px-3 py-1.5 text-xs" disabled={pending} onClick={() => void generate()}>{pending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Sparkles className="h-3.5 w-3.5" />}生成深度阅读</button>
    {error && <p className="mt-2 text-xs text-red-500">{error}</p>}
  </section>;

  const sourceMap = new Map(draft.sources.map((source) => [source.label, source]));
  return <section className="mt-5 border-t border-gray-100 pt-4 dark:border-slate-700">
    <div className="flex items-center justify-between"><div><h3 className="text-sm font-medium">深度阅读 Draft</h3><p className="text-[11px] text-gray-400">{draft.source_count} 个 AI Source · {draft.effective_mode}</p></div><button type="button" className="text-xs text-primary-600" disabled={pending} onClick={() => void generate()}>重新生成</button></div>
    <div className="mt-3 space-y-2">{FIELDS.map(([key, label]) => <FieldCard key={key} label={label} field={draft[key]} sourceMap={sourceMap} onOpen={onOpenCitation} />)}</div>
    {draft.contributions.length > 0 && <div className="mt-4"><p className="mb-2 text-xs font-medium">创新点</p>{draft.contributions.map((item, index) => <ContributionCard key={item.client_id} item={item} index={index} sourceMap={sourceMap} onOpen={onOpenCitation} />)}</div>}
    {draft.experiments.length > 0 && <div className="mt-4"><p className="mb-2 text-xs font-medium">实验</p>{draft.experiments.map((item, index) => <ExperimentCard key={item.client_id} item={item} index={index} sourceMap={sourceMap} onOpen={onOpenCitation} />)}</div>}
    <div className="mt-5 rounded-lg border border-gray-200 p-3 dark:border-slate-700"><p className="text-xs font-medium">显式应用到研究笔记</p><select className="input mt-2 py-1.5 text-xs" value={destination} onChange={(event) => setDestination(event.target.value)}><option value="new">新建 Research Note</option>{researchNotes.map((note) => <option key={note.id} value={note.id}>{note.title}</option>)}</select>
      <label className="mt-2 flex items-start gap-2 text-xs"><input type="checkbox" checked={groundedOnly} onChange={(event) => setGroundedOnly(event.target.checked)} />只应用有可信 AI Source 的字段和卡片</label>
      <label className="mt-2 flex items-start gap-2 text-xs"><input type="checkbox" checked={overwrite} onChange={(event) => setOverwrite(event.target.checked)} />覆盖已有标量内容（默认只填空字段）</label>
      <label className="mt-2 block text-xs">创新点与实验：<select className="ml-1 rounded border bg-transparent px-1 py-0.5" value={collectionMode} onChange={(event) => setCollectionMode(event.target.value as "append" | "replace")}><option value="append">追加 AI 卡片</option><option value="replace">替换全部卡片</option></select></label>
      <p className="mt-2 text-[11px] leading-4 text-gray-400">AI Source 仅用于审阅，不会创建 Annotation 或 NoteEvidence；“我的思考”永不由 AI 覆盖。</p>
      <button type="button" className="btn-primary mt-3 w-full justify-center px-3 py-1.5 text-xs" disabled={applying} onClick={() => void apply()}>{applying ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <CheckCircle2 className="h-3.5 w-3.5" />}确认并应用</button>{applyError && <p className="mt-2 text-xs text-red-500">{applyError}</p>}
    </div>
  </section>;
}

function SourceChips({ refs, sourceMap, onOpen }: { refs: string[]; sourceMap: Map<string, AICitation>; onOpen: (citation: AICitation) => void }) { return <div className="mt-2 flex flex-wrap gap-1">{refs.map((ref) => { const source = sourceMap.get(ref); return source ? <button key={ref} type="button" className="rounded bg-primary-50 px-1.5 py-0.5 text-[10px] text-primary-700" onClick={() => onOpen(source)}>[{ref}] {source.page_start ? `p.${source.page_start}` : source.section_title || "原文"}</button> : null; })}</div>; }
function FieldCard({ label, field, sourceMap, onOpen }: { label: string; field: GroundedStructuredField; sourceMap: Map<string, AICitation>; onOpen: (citation: AICitation) => void }) { return <article className="rounded-lg border border-gray-200 p-2.5 dark:border-slate-700"><div className="flex justify-between"><h4 className="text-xs font-medium">{label}</h4><span className={`text-[10px] ${field.grounded ? "text-green-600" : "text-amber-600"}`}>{field.grounded ? "Grounded" : "证据不足"}</span></div><p className="mt-1 whitespace-pre-wrap text-xs leading-5 text-gray-600 dark:text-gray-300">{field.content || "未找到足够证据"}</p><SourceChips refs={field.evidence_refs} sourceMap={sourceMap} onOpen={onOpen} /></article>; }
function ContributionCard({ item, index, sourceMap, onOpen }: { item: DeepReadingContribution; index: number; sourceMap: Map<string, AICitation>; onOpen: (citation: AICitation) => void }) { return <article className="mb-2 rounded-lg bg-gray-50 p-2.5 text-xs dark:bg-slate-800"><p className="font-medium">创新点 {index + 1}</p><p className="mt-1"><b>问题：</b>{item.problem}</p><p><b>前人局限：</b>{item.prior_limitation}</p><p><b>创新：</b>{item.innovation}</p><p><b>方案：</b>{item.solution}</p><SourceChips refs={item.evidence_refs} sourceMap={sourceMap} onOpen={onOpen} /></article>; }
function ExperimentCard({ item, index, sourceMap, onOpen }: { item: DeepReadingExperiment; index: number; sourceMap: Map<string, AICitation>; onOpen: (citation: AICitation) => void }) { return <article className="mb-2 rounded-lg bg-gray-50 p-2.5 text-xs dark:bg-slate-800"><p className="font-medium">实验 {index + 1}</p><p className="mt-1">{item.task}</p><p className="text-gray-500">{[...item.datasets, ...item.baselines, ...item.metrics].join(" · ")}</p><p className="mt-1">{item.result} {item.conclusion}</p><SourceChips refs={item.evidence_refs} sourceMap={sourceMap} onOpen={onOpen} /></article>; }

function profileDraft(profile: ResearchProfileResponse | null): ResearchProfileDraft {
  if (!profile) return emptyResearchProfile();
  const map = new Map(profile.contributions.map((item, index) => [item.id, `existing-c-${index}-${item.id}`]));
  return { ...profile, contributions: profile.contributions.map((item, index) => ({ ...item, client_id: map.get(item.id) ?? `existing-c-${index}`, evidence_ids: item.evidence_ids })), experiments: profile.experiments.map((item, index) => ({ ...item, client_id: `existing-e-${index}-${item.id}`, supports_contribution_client_ids: item.contribution_ids.map((id) => map.get(id)).filter((id): id is string => Boolean(id)), evidence_ids: item.evidence_ids })) };
}

function buildAggregate(currentResponse: ResearchProfileResponse | null, ai: DeepReadingDraft, options: { overwrite: boolean; groundedOnly: boolean; collectionMode: "append" | "replace" }): ResearchProfileDraft {
  const current = profileDraft(currentResponse);
  const next = { ...current };
  for (const [key] of FIELDS) {
    const field = ai[key];
    if (field.content && (!options.groundedOnly || field.grounded) && (options.overwrite || !current[key])) next[key] = field.content;
  }
  const includedContributions = ai.contributions.filter((item) => !options.groundedOnly || item.grounded);
  const aiContributionIds = new Map(includedContributions.map((item) => [item.client_id, `ai-c-${item.client_id}`]));
  const contributions = includedContributions.map((item) => ({ client_id: aiContributionIds.get(item.client_id)!, problem: item.problem, prior_limitation: item.prior_limitation, innovation: item.innovation, solution: item.solution, evidence_summary: null, evidence_ids: [] }));
  const experiments = ai.experiments.filter((item) => !options.groundedOnly || item.grounded).map((item) => ({ client_id: `ai-e-${item.client_id}`, task: item.task, datasets: item.datasets, baselines: item.baselines, metrics: item.metrics, result: item.result, conclusion: item.conclusion, supports_contribution_client_ids: item.supports_contribution_client_ids.map((id) => aiContributionIds.get(id)).filter((id): id is string => Boolean(id)), evidence_ids: [] }));
  next.contributions = options.collectionMode === "replace" ? contributions : [...current.contributions, ...contributions];
  next.experiments = options.collectionMode === "replace" ? experiments : [...current.experiments, ...experiments];
  next.my_thoughts = current.my_thoughts;
  return next;
}
