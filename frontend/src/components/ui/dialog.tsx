import { useEffect, useRef, type ReactNode } from 'react';

interface DialogProps {
  open: boolean;
  onClose: () => void;
  children: ReactNode;
  title?: string;
}

export function Dialog({ open, onClose, children, title }: DialogProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const el = dialogRef.current;
    if (!el) return;
    if (open && !el.open) {
      el.showModal();
    } else if (!open && el.open) {
      el.close();
    }
  }, [open]);

  return (
    <dialog
      ref={dialogRef}
      onClose={onClose}
      onClick={(e) => {
        if (e.target === dialogRef.current) onClose();
      }}
      className="rounded-xl border border-zinc-700 bg-zinc-900 p-0 backdrop:bg-black/50 max-w-lg w-full"
    >
      {title && (
        <div className="px-6 pt-6 pb-2">
          <h2 className="text-lg font-semibold text-white">{title}</h2>
        </div>
      )}
      <div className="px-6 pb-6 pt-2">{children}</div>
    </dialog>
  );
}
