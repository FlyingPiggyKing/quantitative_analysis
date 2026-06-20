"use client";

/**
 * Shared header for the three stock-detail panels (公司信息, 主营业务构成,
 * 股东持仓研究). Renders the title with a decorative marker (default ❖)
 * and a chevron toggle on the right. Click anywhere on the header row
 * to flip `open` and show/hide the panel's children. The chevron
 * rotates -90° when collapsed.
 */
export default function CollapsibleHeader({
  title,
  marker = "❖",
  open,
  onToggle,
  rightSlot,
}: {
  title: string;
  /** Decorative glyph rendered before the title. Empty string to hide. */
  marker?: string;
  open: boolean;
  onToggle: () => void;
  /** Optional right-aligned slot for sub-titles / captions. The chevron
   *  sits to the right of this slot. */
  rightSlot?: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onToggle}
      aria-expanded={open}
      className="flex items-center justify-between w-full mb-3 sm:mb-4 gap-3 group text-left"
    >
      <h2 className="font-[var(--font-playfair)] text-base sm:text-lg tracking-[0.16em] text-vt-parchment uppercase flex items-center gap-2">
        {marker && <span className="text-vt-brass-400">{marker}</span>}
        <span>{title}</span>
      </h2>
      <div className="flex items-center gap-3 shrink-0">
        {rightSlot}
        <span
          aria-hidden
          className="text-vt-parchment-dim font-[var(--font-geist-mono)] text-base leading-none w-3 text-center inline-block"
        >
          {open ? "−" : "+"}
        </span>
      </div>
    </button>
  );
}