import { Link } from "react-router-dom";
import { Upload, BookOpen, Star, Clock, Search } from "lucide-react";
import { useDeletePaper, usePaper, usePapers } from "@/features/paper/hooks";
import { PaperCard } from "@/components/PaperCard";
import { ImportModal } from "@/components/ImportModal";
import { EditPaperDialog } from "@/features/paper/components/EditPaperDialog";
import { useState } from "react";

export default function Dashboard() {
  const { data: paperPage } = usePapers({ page_size: 5 });
  const [showImportModal, setShowImportModal] = useState(false);
  const [editingPaperId, setEditingPaperId] = useState<string | null>(null);
  const editingPaper = usePaper(editingPaperId ?? undefined);
  const deletePaperMut = useDeletePaper();

  const papers = paperPage?.items ?? [];
  const totalCount = paperPage?.total ?? 0;
  const starredPapers = papers.filter((p) => p.is_starred);

  return (
    <div className="mx-auto max-w-5xl p-6">
      {/* Search bar */}
      <div className="mb-6">
        <Link
          to="/search"
          className="flex w-full items-center gap-3 rounded-xl border border-gray-200 bg-white px-4 py-3 text-sm text-gray-400 hover:border-primary-300 transition-colors"
        >
          <Search className="h-4 w-4" />
          <span>搜索论文、作者、关键词...</span>
        </Link>
      </div>

      {/* Quick stats */}
      <div className="mb-6 grid grid-cols-3 gap-4">
        <div className="card flex items-center gap-3">
          <BookOpen className="h-8 w-8 text-primary-500" />
          <div>
            <p className="text-2xl font-semibold">{totalCount}</p>
            <p className="text-xs text-gray-500">论文总数</p>
          </div>
        </div>
        <div className="card flex items-center gap-3">
          <Star className="h-8 w-8 text-amber-400" />
          <div>
            <p className="text-2xl font-semibold">{starredPapers.length}</p>
            <p className="text-xs text-gray-500">已收藏</p>
          </div>
        </div>
        <div className="card flex items-center gap-3">
          <Clock className="h-8 w-8 text-green-500" />
          <div>
            <p className="text-2xl font-semibold">0</p>
            <p className="text-xs text-gray-500">最近阅读</p>
          </div>
        </div>
      </div>

      {/* Upload */}
      <div className="mb-6">
        <button
          onClick={() => setShowImportModal(true)}
          className="btn-primary w-full justify-center py-3"
        >
          <Upload className="h-4 w-4" />
          导入论文
        </button>
      </div>

      {/* Recent papers */}
      <div>
        <div className="mb-3 flex items-center justify-between">
          <h3 className="text-sm font-medium text-gray-700">最近导入</h3>
          <Link to="/library" className="text-xs text-primary-500 hover:underline">
            查看全部
          </Link>
        </div>
        <div className="space-y-3">
          {papers.map((paper) => (
            <PaperCard key={paper.id} paper={paper} onEdit={setEditingPaperId} />
          ))}
          {papers.length === 0 && (
            <div className="card flex flex-col items-center justify-center py-12 text-gray-400">
              <p className="text-sm">暂无论文，导入第一篇吧</p>
            </div>
          )}
        </div>
      </div>

      {/* Import Modal */}
      {showImportModal && (
        <ImportModal onClose={() => setShowImportModal(false)} />
      )}
      {editingPaper.data && (
        <EditPaperDialog paper={editingPaper.data} onClose={() => setEditingPaperId(null)} onDelete={async (paper) => { await deletePaperMut.mutateAsync(paper.id); }} />
      )}
    </div>
  );
}
