import { api } from "@/services/api";
import type { Keyword } from "./types";

export async function listKeywords(): Promise<Keyword[]> {
  return (await api.get<Keyword[]>("/keywords/")).data;
}
