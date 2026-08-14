import { ChevronRight, ChevronDown } from "lucide-react";
import { useState } from "react";
import clsx from "clsx";

export interface OutlineItem {
  id: string;
  title: string;
  level: number;
  page_start?: number | null;
  page_end?: number | null;
  section_type?: string | null;
  children: OutlineItem[];
}

interface OutlineProps {
  items: OutlineItem[];
  onJumpToPage?: (page: number) => void;
  activePage?: number;
}

export function Outline({ items, onJumpToPage, activePage }: OutlineProps) {
  return (
    <div className="space-y-0.5 p-2">
      {items.map((item) => (
        <OutlineNode
          key={item.id}
          item={item}
          onJumpToPage={onJumpToPage}
          activePage={activePage}
        />
      ))}
    </div>
  );
}

function OutlineNode({
  item,
  onJumpToPage,
  activePage,
}: {
  item: OutlineItem;
  onJumpToPage?: (page: number) => void;
  activePage?: number;
}) {
  const [expanded, setExpanded] = useState(true);
  const hasChildren = item.children.length > 0;
  const isActive = activePage && item.page_start && activePage === item.page_start;

  return (
    <div>
      <div
        className={clsx(
          "flex items-center gap-1 rounded px-2 py-1 text-sm cursor-pointer transition-colors",
          isActive ? "bg-primary-50 text-primary-600" : "text-gray-600 hover:bg-gray-50"
        )}
        style={{ paddingLeft: `${item.level * 12 + 8}px` }}
        onClick={() => {
          if (hasChildren) setExpanded(!expanded);
          if (item.page_start && onJumpToPage) onJumpToPage(item.page_start);
        }}
      >
        {hasChildren && (
          <button className="shrink-0">
            {expanded ? (
              <ChevronDown className="h-3 w-3" />
            ) : (
              <ChevronRight className="h-3 w-3" />
            )}
          </button>
        )}
        <span className="truncate">{item.title}</span>
        {item.page_start && (
          <span className="ml-auto text-xs text-gray-400">{item.page_start}</span>
        )}
      </div>
      {hasChildren && expanded && (
        <div>
          {item.children.map((child) => (
            <OutlineNode
              key={child.id}
              item={child}
              onJumpToPage={onJumpToPage}
              activePage={activePage}
            />
          ))}
        </div>
      )}
    </div>
  );
}
