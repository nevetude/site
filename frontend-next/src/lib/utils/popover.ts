/**
 * Shows `el` as a manual popover under `anchor` (above it when the page ends below). A popover lives in the top layer,
 * so a card with `overflow: hidden` cannot cut it. It is closed through `onclose` by a press outside, by Escape and
 * when the page scrolls or is resized (a menu that stayed behind its button would look broken). Returns what puts it away.
 * `matchWidth`: a list is exactly as wide as its button (its `min-width` if that is more), so its size never depends on
 * what is in it; a calendar keeps the width of its own content.
 */
export function openPopover(
	el: HTMLElement,
	anchor: HTMLElement,
	onclose: () => void,
	matchWidth = true
) {
	el.showPopover();
	place(el, anchor, matchWidth);

	const outside = (event: Event) => event.target instanceof Node && !el.contains(event.target);
	const pressed = (event: PointerEvent) => {
		if (outside(event) && !anchor.contains(event.target as Node)) onclose();
	};
	const key = (event: KeyboardEvent) => {
		if (event.key !== 'Escape') return;
		// Escape must not also close the dialog that the popover stands in.
		event.preventDefault();
		event.stopPropagation();
		onclose();
		anchor.focus();
	};
	const scrolled = (event: Event) => outside(event) && onclose();

	document.addEventListener('pointerdown', pressed, true);
	document.addEventListener('keydown', key, true);
	window.addEventListener('scroll', scrolled, true);
	window.addEventListener('resize', onclose);
	return () => {
		document.removeEventListener('pointerdown', pressed, true);
		document.removeEventListener('keydown', key, true);
		window.removeEventListener('scroll', scrolled, true);
		window.removeEventListener('resize', onclose);
		if (el.matches(':popover-open')) el.hidePopover();
	};
}

const GAP = 4;
const MARGIN = 8;

function place(el: HTMLElement, anchor: HTMLElement, matchWidth: boolean) {
	const a = anchor.getBoundingClientRect();
	if (matchWidth)
		el.style.width = `${Math.max(a.width, parseFloat(getComputedStyle(el).minWidth) || 0)}px`;
	const { offsetHeight: height, offsetWidth: width } = el;
	const below = a.bottom + GAP;
	const flip = below + height > innerHeight - MARGIN && a.top - GAP - height >= MARGIN;
	el.style.top = `${flip ? a.top - GAP - height : below}px`;
	el.style.left = `${Math.max(MARGIN, Math.min(a.left, innerWidth - MARGIN - width))}px`;
}
