import { useState, type ReactNode } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Bot, CircleDollarSign, Loader2, Plus, ShieldAlert, TestTube2 } from "lucide-react";

import { addPricing, createBudget, createModel, createProvider, listBudgets, listModels, listProviders, testProvider, usageRequests, usageSummary } from "@/features/ai-infrastructure/api";

export default function AIUsage() {
  const client = useQueryClient();
  const summary = useQuery({ queryKey: ["ai-usage-summary"], queryFn: usageSummary });
  const requests = useQuery({ queryKey: ["ai-usage-requests"], queryFn: () => usageRequests(1) });
  const providers = useQuery({ queryKey: ["ai-providers"], queryFn: listProviders });
  const models = useQuery({ queryKey: ["ai-models"], queryFn: listModels });
  const budgets = useQuery({ queryKey: ["ai-budgets"], queryFn: listBudgets });
  const [providerOpen, setProviderOpen] = useState(false);
  const [modelOpen, setModelOpen] = useState(false);
  const [budgetOpen, setBudgetOpen] = useState(false);
  const createProviderMutation = useMutation({ mutationFn: createProvider, onSuccess: () => { void client.invalidateQueries({ queryKey: ["ai-providers"] }); setProviderOpen(false); } });
  const createModelMutation = useMutation({
    mutationFn: async (data: { provider_id: string; model_name: string; input: number; cached: number; output: number }) => {
      const model = await createModel(data);
      await addPricing(model.id, { currency: "USD", input_per_million: data.input, cached_input_per_million: data.cached, output_per_million: data.output });
      return model;
    },
    onSuccess: () => { void client.invalidateQueries({ queryKey: ["ai-models"] }); setModelOpen(false); },
  });
  const createBudgetMutation = useMutation({ mutationFn: createBudget, onSuccess: () => { void client.invalidateQueries({ queryKey: ["ai-budgets"] }); setBudgetOpen(false); } });
  const usage = summary.data;

  return <div className="mx-auto max-w-6xl p-6">
    <div className="mb-5"><h1 className="text-xl font-semibold">AI 用量与费用</h1><p className="mt-1 text-sm text-gray-500">统一查看翻译、Reader 问答、Embedding 与深度阅读的真实 Token、费用和预算。</p></div>
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-4"><Metric label="请求" value={usage?.request_count ?? 0} /><Metric label="总 Token" value={(usage?.total_tokens ?? 0).toLocaleString()} /><Metric label="已计算费用" value={usage?.currency ? `${usage.currency} ${usage.calculated_cost}` : "—"} /><Metric label="未知费用请求" value={usage?.unknown_cost_requests ?? 0} warn={Boolean(usage?.unknown_cost_requests)} /></div>

    <section className="card mt-4">
      <Header icon={Bot} title="Provider 与模型" action={<div className="flex gap-2"><button className="btn-ghost text-xs" onClick={() => setProviderOpen(value => !value)}><Plus className="h-3.5 w-3.5" />Provider</button><button className="btn-ghost text-xs" onClick={() => setModelOpen(value => !value)} disabled={!providers.data?.length}><Plus className="h-3.5 w-3.5" />模型</button></div>} />
      {providerOpen && <form className="mb-3 grid gap-2 rounded-lg bg-gray-50 p-3 md:grid-cols-4 dark:bg-slate-800" onSubmit={event => { event.preventDefault(); const form = new FormData(event.currentTarget); createProviderMutation.mutate({ name: String(form.get("name")), base_url: String(form.get("url")), api_key: String(form.get("key")), is_local: form.get("local") === "on" }); }}><input required name="name" className="input text-sm" placeholder="Provider 名称" /><input required name="url" className="input text-sm" placeholder="https://…/v1" /><input required type="password" name="key" className="input text-sm" placeholder="API Key" /><label className="flex items-center gap-2 text-xs"><input type="checkbox" name="local" />本地 Provider</label><button className="btn-primary w-fit text-xs" type="submit">加密保存</button></form>}
      {modelOpen && <form className="mb-3 grid gap-2 rounded-lg bg-gray-50 p-3 md:grid-cols-3 dark:bg-slate-800" onSubmit={event => { event.preventDefault(); const form = new FormData(event.currentTarget); createModelMutation.mutate({ provider_id: String(form.get("provider")), model_name: String(form.get("model")), input: Number(form.get("input")), cached: Number(form.get("cached")), output: Number(form.get("output")) }); }}><select required name="provider" className="input text-sm">{providers.data?.map(provider => <option key={provider.id} value={provider.id}>{provider.name}</option>)}</select><input required name="model" className="input text-sm" placeholder="模型标识" /><span className="text-xs text-gray-500">每百万 Token 单价（USD）</span><input required name="input" min="0" step="0.000001" type="number" className="input text-sm" placeholder="输入" /><input required name="cached" min="0" step="0.000001" type="number" className="input text-sm" placeholder="缓存输入" /><input required name="output" min="0" step="0.000001" type="number" className="input text-sm" placeholder="输出" /><button className="btn-primary w-fit text-xs">添加模型与价格</button></form>}
      <div className="space-y-2">{providers.data?.map(provider => <div key={provider.id} className="flex items-center justify-between rounded-lg border border-gray-100 p-3 text-sm dark:border-slate-700"><div><p className="font-medium">{provider.name} <span className="ml-2 text-xs text-gray-400">{provider.masked_api_key}</span></p><p className="mt-1 text-xs text-gray-400">{provider.base_url} · {provider.is_local ? "本地" : "云端"}</p><p className="mt-1 text-xs text-gray-500">{models.data?.filter(model => model.provider_id === provider.id).map(model => model.model_name).join("、") || "尚未配置模型"}</p></div><button className="btn-ghost text-xs" onClick={() => void testProvider(provider.id).then(result => alert(result.message))}><TestTube2 className="h-3.5 w-3.5" />测试</button></div>)}</div>
    </section>

    <section className="card mt-4"><Header icon={ShieldAlert} title="预算与硬限额" action={<button className="btn-ghost text-xs" onClick={() => setBudgetOpen(value => !value)}><Plus className="h-3.5 w-3.5" />预算</button>} />{budgetOpen && <form className="mb-3 flex flex-wrap gap-2 rounded-lg bg-gray-50 p-3 dark:bg-slate-800" onSubmit={event => { event.preventDefault(); const form = new FormData(event.currentTarget); createBudgetMutation.mutate({ scope_type: "global", period_type: String(form.get("period")), token_limit: Number(form.get("tokens")) || null, cost_limit: Number(form.get("cost")) || null, currency: "USD", hard_limit: true, warning_threshold: .8, enabled: true }); }}><select name="period" className="input w-32 text-sm"><option value="daily">每日</option><option value="monthly">每月</option><option value="per_request">单次</option></select><input name="tokens" type="number" min="1" className="input w-40 text-sm" placeholder="Token 上限" /><input name="cost" type="number" min="0" step="0.01" className="input w-40 text-sm" placeholder="费用上限 USD" /><button className="btn-primary text-xs">保存硬限额</button></form>}<div className="flex flex-wrap gap-2">{budgets.data?.map(budget => <span key={budget.id} className="rounded-full bg-amber-50 px-3 py-1.5 text-xs text-amber-800">{budget.period_type} · {budget.token_limit ? `${budget.token_limit.toLocaleString()} Token` : ""} {budget.cost_limit ? `USD ${budget.cost_limit}` : ""}</span>)}{!budgets.data?.length && <p className="text-sm text-gray-400">尚未设置预算。</p>}</div></section>

    <section className="card mt-4"><Header icon={CircleDollarSign} title="请求明细" /><div className="overflow-x-auto"><table className="w-full text-left text-xs"><thead className="text-gray-400"><tr><th className="py-2">时间</th><th>功能</th><th>状态</th><th>输入</th><th>输出</th><th>费用</th><th>耗时</th></tr></thead><tbody>{requests.data?.items.map(request => <tr key={request.id} className="border-t border-gray-100 dark:border-slate-700"><td className="py-2">{new Date(request.created_at).toLocaleString()}</td><td>{request.feature}</td><td>{request.status}</td><td>{request.input_tokens ?? "—"}</td><td>{request.output_tokens ?? "—"}</td><td>{request.cost_status === "unknown" ? "未知" : request.actual_cost ? `${request.currency} ${request.actual_cost}` : "—"}</td><td>{request.duration_ms ? `${request.duration_ms}ms` : "—"}</td></tr>)}</tbody></table>{requests.isLoading && <Loader2 className="mx-auto my-5 h-5 w-5 animate-spin" />}</div></section>
  </div>;
}

function Metric({ label, value, warn = false }: { label: string; value: string | number; warn?: boolean }) { return <div className="card"><p className="text-xs text-gray-400">{label}</p><p className={`mt-2 text-xl font-semibold ${warn ? "text-amber-600" : ""}`}>{value}</p></div>; }
function Header({ icon: Icon, title, action }: { icon: typeof Bot; title: string; action?: ReactNode }) { return <div className="mb-3 flex items-center justify-between"><h2 className="flex items-center gap-2 text-sm font-semibold"><Icon className="h-4 w-4 text-primary-500" />{title}</h2>{action}</div>; }
