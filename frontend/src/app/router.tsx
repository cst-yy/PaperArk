import { lazy, Suspense } from "react";
import { Loader2 } from "lucide-react";
import { Navigate, Route, Routes } from "react-router-dom";
import { AppLayout } from "./layout";

const Dashboard = lazy(() => import("@/pages/Dashboard"));
const Library = lazy(() => import("@/pages/Library"));
const PaperList = lazy(() => import("@/pages/PaperList"));
const Reader = lazy(() => import("@/pages/Reader"));
const Notes = lazy(() => import("@/pages/Notes"));
const Search = lazy(() => import("@/pages/Search"));
const Settings = lazy(() => import("@/pages/Settings"));
const AIUsage = lazy(() => import("@/pages/AIUsage"));
const CitationGraph = lazy(() => import("@/pages/CitationGraph"));
const KnowledgeGraph = lazy(() => import("@/pages/KnowledgeGraph"));
const MindMap = lazy(() => import("@/pages/MindMap"));

function RouteLoading() {
  return <div className="flex h-full min-h-[320px] items-center justify-center text-sm text-gray-500">
    <Loader2 className="mr-2 h-4 w-4 animate-spin" />正在加载页面…
  </div>;
}

export function AppRouter() {
  return (
    <Suspense fallback={<RouteLoading />}><Routes>
      <Route element={<AppLayout />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/library" element={<Library />} />
        <Route path="/papers" element={<PaperList />} />
        <Route path="/favorites" element={<Navigate to="/library?starred=true" replace />} />
        <Route path="/notes" element={<Notes />} />
        <Route path="/notes/:noteId" element={<Notes />} />
        <Route path="/papers/:paperId/notes" element={<Notes />} />
        <Route path="/search" element={<Search />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="/settings/ai-usage" element={<AIUsage />} />
        <Route path="/graph/citations" element={<CitationGraph />} />
        <Route path="/graph/knowledge" element={<KnowledgeGraph />} />
        <Route path="/mind-map" element={<MindMap />} />
      </Route>

      <Route path="/reader/:paperId" element={<Reader />} />
    </Routes></Suspense>
  );
}
