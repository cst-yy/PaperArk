import { api } from "@/services/api";
import type { DashboardData, ReadingTrend } from "./types";

export async function getDashboard(topicDays: 7 | 30, topicLimit: 20 | 50): Promise<DashboardData> {
  return (await api.get<DashboardData>("/dashboard/", { params: { topic_days: topicDays, topic_limit: topicLimit } })).data;
}

export async function getReadingTrend(days: 7 | 30 | 90): Promise<ReadingTrend> {
  return (await api.get<ReadingTrend>("/dashboard/reading-trend", { params: { days } })).data;
}
