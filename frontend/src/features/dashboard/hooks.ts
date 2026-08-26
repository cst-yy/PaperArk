import { useQuery } from "@tanstack/react-query";
import { getDashboard, getReadingTrend } from "./api";

export function useDashboard(topicDays: 7 | 30 = 30, topicLimit: 20 | 50 = 20) {
  return useQuery({ queryKey: ["dashboard", topicDays, topicLimit], queryFn: () => getDashboard(topicDays, topicLimit), gcTime: 5 * 60_000 });
}

export function useReadingTrend(days: 7 | 30 | 90) {
  return useQuery({ queryKey: ["dashboard-reading-trend", days], queryFn: () => getReadingTrend(days), gcTime: 5 * 60_000 });
}
