import {useMutation,useQuery,useQueryClient} from "@tanstack/react-query";
import {getMyPaperStats,getResearchIdentity,listIdentityCandidates,setResearchIdentity} from "./api";
export const useResearchIdentity=()=>useQuery({queryKey:["research-identity"],queryFn:getResearchIdentity});
export const useIdentityCandidates=()=>useQuery({queryKey:["research-identity","candidates"],queryFn:listIdentityCandidates});
export const useMyPaperStats=()=>useQuery({queryKey:["research-identity","stats"],queryFn:getMyPaperStats});
export const useSetResearchIdentity=()=>{const client=useQueryClient();return useMutation({mutationFn:setResearchIdentity,onSuccess:()=>{void client.invalidateQueries({queryKey:["research-identity"]});void client.invalidateQueries({queryKey:["papers"]});}})};
