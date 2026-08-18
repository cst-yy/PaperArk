import { Route, Routes } from "react-router-dom";
import { AppLayout } from "./layout";

import Dashboard from "@/pages/Dashboard";
import Library from "@/pages/Library";
import Reader from "@/pages/Reader";
import Notes from "@/pages/Notes";
import Search from "@/pages/Search";
import Settings from "@/pages/Settings";
import CitationGraph from "@/pages/CitationGraph";
import KnowledgeGraph from "@/pages/KnowledgeGraph";
import MindMap from "@/pages/MindMap";

export function AppRouter() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/library" element={<Library />} />
        <Route path="/notes" element={<Notes />} />
        <Route path="/notes/:noteId" element={<Notes />} />
        <Route path="/papers/:paperId/notes" element={<Notes />} />
        <Route path="/search" element={<Search />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="/graph/citations" element={<CitationGraph />} />
        <Route path="/graph/knowledge" element={<KnowledgeGraph />} />
        <Route path="/mind-map" element={<MindMap />} />
      </Route>

      <Route path="/reader/:paperId" element={<Reader />} />
    </Routes>
  );
}
