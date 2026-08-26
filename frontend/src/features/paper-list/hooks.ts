import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { batchDeletePapers, batchUpdatePapers, getPaperList, getPaperListPreference, getPaperListViewSettings, savePaperListPreference, updatePaperCell } from "./api";
import type { PaperListQuery } from "./types";

export function usePaperList(query: PaperListQuery) {
  return useQuery({ queryKey: ["paper-list", query], queryFn: () => getPaperList(query), placeholderData: (previous) => previous });
}
export function usePaperListPreference() { return useQuery({ queryKey: ["paper-list-preference"], queryFn: getPaperListPreference }); }
export function usePaperListViewSettingsQuery() { return useQuery({queryKey:["paper-list-view-settings"],queryFn:getPaperListViewSettings}); }
export function useSavePaperListPreference() { const client = useQueryClient(); return useMutation({ mutationFn: savePaperListPreference, onSuccess: (value) => client.setQueryData(["paper-list-preference"], value) }); }
export function useUpdatePaperCell() { const client = useQueryClient(); return useMutation({ mutationFn: ({paperId,data}:{paperId:string;data:import("./types").PaperCellUpdate}) => updatePaperCell(paperId,data), onSuccess: (_, variables) => { client.invalidateQueries({queryKey:["paper-list"]}); client.invalidateQueries({queryKey:["paper",variables.paperId]}); client.invalidateQueries({queryKey:["papers"]}); } }); }
export function useBatchUpdatePapers() { const client=useQueryClient(); return useMutation({mutationFn:batchUpdatePapers,onSuccess:()=>{client.invalidateQueries({queryKey:["paper-list"]});client.invalidateQueries({queryKey:["papers"]});client.invalidateQueries({queryKey:["paper"]});}}); }
export function useBatchDeletePapers() { const client=useQueryClient(); return useMutation({mutationFn:batchDeletePapers,onSuccess:()=>{client.invalidateQueries({queryKey:["paper-list"]});client.invalidateQueries({queryKey:["papers"]});}}); }
