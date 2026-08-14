import { Route, Routes } from "react-router-dom";
import { AppLayout } from "./layout";

import Dashboard from "@/pages/Dashboard";
import Library from "@/pages/Library";
import Reader from "@/pages/Reader";
import Notes from "@/pages/Notes";
import Search from "@/pages/Search";
import Settings from "@/pages/Settings";

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
      </Route>

      <Route path="/reader/:paperId" element={<Reader />} />
    </Routes>
  );
}
