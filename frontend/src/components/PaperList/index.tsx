import { PaperCard } from "@/components/PaperCard";
import type { PaperListItem } from "@/features/paper/types";

interface PaperListProps {
  papers: PaperListItem[];
  onToggleStar?: (id: string) => void;
  onEdit?: (id: string) => void;
}

export function PaperList({ papers, onToggleStar, onEdit }: PaperListProps) {
  if (papers.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-gray-400">
        <p className="text-sm">暂无论文</p>
        <p className="mt-1 text-xs">点击「导入 PDF」或「手动添加」开始</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {papers.map((paper) => (
        <PaperCard
          key={paper.id}
          paper={paper}
          onToggleStar={onToggleStar}
          onEdit={onEdit}
        />
      ))}
    </div>
  );
}
