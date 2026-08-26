import { useEffect, useRef, useState } from "react";
import { getPaperListViewSettings, patchPaperListViewSettings } from "./api";
import { sanitizeViewSettings } from "./paperListSettingsSchema";
import type { PaperListSettingsSection, PaperListViewSettings } from "./types";

const LOCAL_KEY="paperark.paper-list.view.v2.default-user";
function localMirror():PaperListViewSettings|null{try{const raw=localStorage.getItem(LOCAL_KEY);return raw?sanitizeViewSettings(JSON.parse(raw)):null;}catch{return null;}}

export function usePaperListViewSettings(server:PaperListViewSettings){
  const [settings,setSettings]=useState<PaperListViewSettings>(()=>{const local=localMirror();const clean=sanitizeViewSettings(server);return local&&local.revision>=clean.revision?local:clean;});
  const revision=useRef(settings.revision);const timers=useRef<Partial<Record<PaperListSettingsSection,ReturnType<typeof setTimeout>>>>({});
  useEffect(()=>()=>{Object.values(timers.current).forEach(timer=>clearTimeout(timer));},[]);
  const persist=async(section:PaperListSettingsSection,value:unknown)=>{
    try{const saved=await patchPaperListViewSettings(section,value,revision.current);revision.current=saved.revision;setSettings(current=>{const next={...current,revision:saved.revision};localStorage.setItem(LOCAL_KEY,JSON.stringify(next));return next;});}
    catch(error){if((error as {response?:{status?:number}}).response?.status!==409)return;const latest=await getPaperListViewSettings();revision.current=latest.revision;const saved=await patchPaperListViewSettings(section,value,latest.revision);revision.current=saved.revision;setSettings(current=>{const next={...current,revision:saved.revision};localStorage.setItem(LOCAL_KEY,JSON.stringify(next));return next;});}
  };
  const updateSection=<K extends PaperListSettingsSection>(section:K,value:PaperListViewSettings[K],delay=400)=>{setSettings(current=>{const next={...current,[section]:value};localStorage.setItem(LOCAL_KEY,JSON.stringify(next));return next;});const previous=timers.current[section];if(previous)clearTimeout(previous);timers.current[section]=setTimeout(()=>void persist(section,value),delay);};
  const resetAll=()=>{const next=sanitizeViewSettings(null);setSettings(next);localStorage.setItem(LOCAL_KEY,JSON.stringify(next));(["columns","appearance","query","layout"] as PaperListSettingsSection[]).forEach(section=>updateSection(section,next[section],0));};
  return {settings,updateSection,resetAll};
}
