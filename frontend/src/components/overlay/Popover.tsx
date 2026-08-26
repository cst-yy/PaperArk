/* eslint-disable react-refresh/only-export-components -- hook is the headless form of the same primitive */
import { useContext, useEffect, useId, useRef, type ReactElement, type ReactNode, type RefObject } from "react";

import { OverlayContext, type OverlayDismissReason } from "./OverlayProvider";

interface TriggerProps {
  onClick?: React.MouseEventHandler<HTMLElement>;
  "aria-expanded"?: boolean;
  "aria-controls"?: string;
  "aria-haspopup"?: "menu" | "listbox" | "dialog" | true;
}

interface PopoverProps {
  open: boolean;
  onOpenChange: (open: boolean, reason: OverlayDismissReason | "trigger") => void;
  trigger: (props: TriggerProps) => ReactElement;
  children: ReactNode;
  group?: string;
  parentId?: string;
  contentClassName?: string;
  role?: "menu" | "listbox" | "dialog";
}

export function Popover({ open, onOpenChange, trigger, children, group = "root", parentId, contentClassName, role = "menu" }: PopoverProps) {
  const triggerRef = useRef<HTMLDivElement>(null);
  const contentRef = useRef<HTMLDivElement>(null);
  const id = useDismissibleLayer({ open, onOpenChange, triggerRef, contentRef, group, parentId });

  const renderedTrigger = trigger({
    onClick: (event: React.MouseEvent<HTMLElement>) => {
      if (!event.defaultPrevented) onOpenChange(!open, "trigger");
    },
    "aria-expanded": open,
    "aria-controls": open ? `${id}-content` : undefined,
    "aria-haspopup": role,
  });

  return <div ref={triggerRef} className="relative">
    {renderedTrigger}
    {open && <div ref={contentRef} id={`${id}-content`} role={role} className={contentClassName}>{children}</div>}
  </div>;
}

export function useDismissibleLayer({ open, onOpenChange, triggerRef, contentRef, group = "root", parentId }: {
  open: boolean;
  onOpenChange: (open: boolean, reason: OverlayDismissReason | "trigger") => void;
  triggerRef: RefObject<HTMLElement | null>;
  contentRef: RefObject<HTMLElement | null>;
  group?: string;
  parentId?: string;
}) {
  const stack = useContext(OverlayContext);
  const reactId = useId();
  const id = `popover-${reactId.replace(/:/g, "")}`;
  const onOpenChangeRef = useRef(onOpenChange);
  useEffect(() => { onOpenChangeRef.current = onOpenChange; }, [onOpenChange]);
  useEffect(() => {
    if (!open || !stack) return;
    return stack.register({ id, group, parentId, triggerRef, contentRef, onDismiss: (reason) => {
      onOpenChangeRef.current(false, reason);
      if (reason === "escape") queueMicrotask(() => {
        const target = triggerRef.current;
        if (target instanceof HTMLButtonElement) target.focus();
        else target?.querySelector<HTMLElement>("button,[href],input,select,textarea,[tabindex]:not([tabindex='-1'])")?.focus();
      });
    } });
  }, [contentRef, group, id, open, parentId, stack, triggerRef]);
  return id;
}
