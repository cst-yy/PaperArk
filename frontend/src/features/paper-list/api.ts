import { api } from "@/services/api";
import type { PaperCellUpdate, PaperListPage, PaperListPreference, PaperListQuery, PaperListRow, PaperListSettingsSection, PaperListViewSettings } from "./types";

export async function getPaperList(query: PaperListQuery): Promise<PaperListPage> {
  return (await api.get<PaperListPage>("/paper-list/", { params: query })).data;
}
export async function updatePaperCell(paperId: string, data: PaperCellUpdate): Promise<PaperListRow> {
  return (await api.patch(`/papers/${paperId}`, data)).data;
}
export async function getPaperListPreference(): Promise<PaperListPreference> { return (await api.get("/paper-list/preference")).data; }
export async function savePaperListPreference(value: PaperListPreference): Promise<PaperListPreference> { return (await api.put("/paper-list/preference", value)).data; }
export async function batchUpdatePapers(data: Record<string, unknown>): Promise<{updated:number}> { return (await api.post("/paper-list/batch-update", data)).data; }
export async function batchDeletePapers(paperIds: string[]): Promise<{deleted:number}> { return (await api.post("/paper-list/batch-delete", { paper_ids: paperIds })).data; }
export async function getPaperListViewSettings(): Promise<PaperListViewSettings> { return (await api.get("/paper-list/view-settings")).data; }
export async function patchPaperListViewSettings(section: PaperListSettingsSection, value: unknown, expectedRevision: number): Promise<PaperListViewSettings> { return (await api.patch("/paper-list/view-settings", {expected_revision:expectedRevision,[section]:value})).data; }
