import {useState} from "react";
import {Fingerprint,Loader2} from "lucide-react";
import {useIdentityCandidates,useResearchIdentity,useSetResearchIdentity} from "./hooks";

export function ResearchIdentitySettings(){
  const identity=useResearchIdentity(),candidates=useIdentityCandidates(),save=useSetResearchIdentity();
  const error=(save.error as {response?:{data?:{detail?:string|{msg?:string}[]}}}|null)?.response?.data?.detail;
  const errorText=typeof error==="string"?error:Array.isArray(error)?error.map(item=>item.msg).filter(Boolean).join("；"):"保存失败，请检查输入后重试。";
  return <><IdentityForm key={`${identity.data?.id??"new"}:${identity.data?.author_id??""}`} identity={identity.data??null} candidates={candidates.data??[]} pending={save.isPending} onSave={data=>save.mutate(data)}/>{save.isSuccess?<p className="-mt-2 mb-4 text-xs text-emerald-600">研究身份已保存。</p>:null}{save.isError?<p className="-mt-2 mb-4 text-xs text-red-600">{errorText}</p>:null}</>;
}

function IdentityForm({identity,candidates,pending,onSave}:{identity:import("./api").ResearchIdentity|null;candidates:import("./api").IdentityCandidate[];pending:boolean;onSave:(data:import("./api").ResearchIdentityInput)=>void}){
  const[authorId,setAuthorId]=useState(identity?.author_id??"");const[displayName,setDisplayName]=useState(identity?.display_name??"");const[orcid,setOrcid]=useState(identity?.orcid??"");const[email,setEmail]=useState(identity?.email??"");
  const selected=candidates.find(item=>item.author_id===authorId);
  return <section className="card mb-4"><div className="mb-4 flex items-center gap-2"><Fingerprint className="h-4 w-4 text-violet-500"/><div><h2 className="text-sm font-semibold">研究身份</h2><p className="text-xs text-gray-500">单位仅用于帮助选择候选，不保存为身份条件；ORCID 和邮箱均可不填。</p></div></div>
    <div className="grid gap-3 md:grid-cols-2"><label className="text-sm"><span className="mb-1 block text-xs text-gray-500">作者身份</span><select className="input" value={authorId} onChange={event=>{setAuthorId(event.target.value);const item=candidates.find(row=>row.author_id===event.target.value);if(item&&!displayName)setDisplayName(item.name)}}><option value="">选择作者…</option>{candidates.map(item=><option key={item.author_id} value={item.author_id}>{item.name}{item.affiliation?` · ${item.affiliation}`:""}（{item.paper_count} 篇）</option>)}</select></label><label className="text-sm"><span className="mb-1 block text-xs text-gray-500">显示名称</span><input className="input" value={displayName} placeholder={selected?.name??"用于页面展示"} onChange={event=>setDisplayName(event.target.value)}/></label><label className="text-sm"><span className="mb-1 block text-xs text-gray-500">ORCID（可选）</span><input className="input" value={orcid} placeholder="0000-0000-0000-0000" onChange={event=>setOrcid(event.target.value)}/></label><label className="text-sm"><span className="mb-1 block text-xs text-gray-500">邮箱（可选）</span><input className="input" type="email" value={email} onChange={event=>setEmail(event.target.value)}/></label></div>
    <div className="mt-4 flex items-center justify-between"><p className="text-xs text-gray-500">当前绑定只以内部 Author ID 判断“我的论文”。</p><button className="btn-primary" disabled={!authorId||pending} onClick={()=>onSave({author_id:authorId,display_name:displayName.trim()||selected?.name||null,orcid:orcid.trim()||null,email:email.trim()||null})}>{pending?<Loader2 className="h-4 w-4 animate-spin"/>:null}保存研究身份</button></div>
  </section>
}
