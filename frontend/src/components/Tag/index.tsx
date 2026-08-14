import clsx from "clsx";
import { getStableColor } from "@/utils";

interface TagProps {
  name: string;
  color?: string;
  active?: boolean;
  onClick?: () => void;
}

export function Tag({ name, color, active, onClick }: TagProps) {
  return (
    <button
      onClick={onClick}
      className={clsx(
        "inline-flex items-center rounded-md px-2 py-0.5 text-xs transition-opacity",
        active ? "opacity-100" : "opacity-70 hover:opacity-100"
      )}
      style={{ backgroundColor: color || getStableColor(name) }}
    >
      {name}
    </button>
  );
}
