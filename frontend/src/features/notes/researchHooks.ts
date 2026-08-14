import { useMutation,useQuery,useQueryClient } from "@tanstack/react-query";
import { getResearchProfile,saveResearchProfile } from "./researchApi";
export const researchKey=(id:string)=>["notes","research-profile",id] as const;
export function useResearchProfile(id:string){return useQuery({queryKey:researchKey(id),queryFn:()=>getResearchProfile(id)});}
export function useSaveResearchProfile(id:string){const client=useQueryClient();return useMutation({mutationFn:(data:Parameters<typeof saveResearchProfile>[1])=>saveResearchProfile(id,data),onSuccess:(data)=>client.setQueryData(researchKey(id),data)});}
