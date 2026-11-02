import { tick } from 'svelte';
import type { ArtistAlbum } from '#lib/api/client.js';

const THRESHOLD = 5; // px the pointer must go before a press is a drag
const EDGE = 90; // px from the top or the bottom of the window where the page starts to scroll
const SCROLL = 18; // px per frame at the very edge
const FLIGHT = 340; // ms the card in the hand takes to fly to its place
const FLIGHT_EASING = 'cubic-bezier(0.22, 1, 0.36, 1)';

/**
 * A release taken with the pointer and carried over the categories of an artist (edit mode). The card is copied and the
 * copy follows the pointer (lifted, a little tilted, with a shadow), the original stays dimmed in its place. The
 * category under the pointer (an element with `data-category`) is told to light up. On release over another category
 * `onmove` is called, the card flies to the place it takes there and shows when it has landed; over nothing it flies
 * back. The page scrolls while the pointer is near its top or bottom edge. Escape lets go of the card.
 */
export class ReleaseDrag {
	/** The release in the hand, and the category it came from. */
	album = $state<ArtistAlbum | null>(null);
	from = $state('');
	/** The category under the pointer; null over none. */
	over = $state<string | null>(null);
	/** The place (`category|album`) a release is flying to: its card there stays hidden until it has landed. */
	landing = $state<string | null>(null);

	private pressed: {
		album: ArtistAlbum;
		from: string;
		card: HTMLElement;
		rect: DOMRect;
		x: number;
		y: number;
	} | null = null;
	private ghost: HTMLElement | null = null;
	private pointer = { x: 0, y: 0 };
	private frame = 0;

	/** `onmove` answers false when the drop changed nothing (the card then goes back to where it was). */
	constructor(
		private readonly onmove: (album: ArtistAlbum, type: string, from: string) => boolean | void
	) {}

	/** A press on a card of the category `from`. */
	press(event: PointerEvent, album: ArtistAlbum, from: string, card: HTMLElement) {
		if (event.button !== 0 || this.pressed || this.album) return;
		this.pressed = {
			album,
			from,
			card,
			rect: card.getBoundingClientRect(),
			x: event.clientX,
			y: event.clientY
		};
		this.pointer = { x: event.clientX, y: event.clientY };
		window.addEventListener('pointermove', this.move);
		window.addEventListener('pointerup', this.release);
		window.addEventListener('pointercancel', this.release);
		window.addEventListener('keydown', this.key);
	}

	destroy() {
		this.unlisten();
		cancelAnimationFrame(this.frame);
		this.ghost?.remove();
		document.documentElement.classList.remove('dragging');
	}

	private unlisten() {
		window.removeEventListener('pointermove', this.move);
		window.removeEventListener('pointerup', this.release);
		window.removeEventListener('pointercancel', this.release);
		window.removeEventListener('keydown', this.key);
	}

	private move = (event: PointerEvent) => {
		this.pointer = { x: event.clientX, y: event.clientY };
		const press = this.pressed;
		if (!press) return;
		if (!this.ghost) {
			if (Math.hypot(event.clientX - press.x, event.clientY - press.y) < THRESHOLD) return;
			this.lift(press);
		}
		this.follow();
	};

	private lift(press: NonNullable<ReleaseDrag['pressed']>) {
		const ghost = press.card.cloneNode(true) as HTMLElement;
		ghost.removeAttribute('data-album');
		ghost.removeAttribute('data-category');
		Object.assign(ghost.style, {
			position: 'fixed',
			left: `${press.rect.left}px`,
			top: `${press.rect.top}px`,
			width: `${press.rect.width}px`,
			height: `${press.rect.height}px`,
			margin: '0',
			zIndex: '60',
			pointerEvents: 'none',
			opacity: '1',
			borderRadius: '0.5rem',
			background: 'var(--card)',
			willChange: 'transform',
			// scale and rotate are properties of their own: they ease while `transform` follows the pointer at once
			transition: 'scale 180ms ease-out, rotate 180ms ease-out, box-shadow 180ms ease-out',
			boxShadow: '0 0 0 rgba(0,0,0,0)'
		});
		document.body.append(ghost);
		this.ghost = ghost;
		this.album = press.album;
		this.from = press.from;
		document.documentElement.classList.add('dragging');
		requestAnimationFrame(() => {
			ghost.style.scale = '1.05';
			ghost.style.rotate = '2deg';
			ghost.style.boxShadow = '0 18px 36px rgba(0, 0, 0, 0.5)';
		});
		this.scrolling();
	}

	private follow() {
		const press = this.pressed;
		if (!press || !this.ghost) return;
		this.ghost.style.transform = `translate(${this.pointer.x - press.x}px, ${this.pointer.y - press.y}px)`;
	}

	/** Every frame: scroll near the edge, and see which category is under the pointer. */
	private scrolling = () => {
		if (!this.ghost) return;
		const { y } = this.pointer;
		const height = window.innerHeight;
		const speed =
			y < EDGE
				? -(1 - y / EDGE) * SCROLL
				: y > height - EDGE
					? (1 - (height - y) / EDGE) * SCROLL
					: 0;
		if (speed) window.scrollBy(0, speed);
		const under = document
			.elementsFromPoint(this.pointer.x, this.pointer.y)
			.find(
				(el): el is HTMLElement => el instanceof HTMLElement && el.dataset.category !== undefined
			);
		this.over = under?.dataset.category ?? null;
		this.frame = requestAnimationFrame(this.scrolling);
	};

	private key = (event: KeyboardEvent) => {
		if (event.key === 'Escape' && this.ghost) {
			event.stopPropagation();
			this.over = null;
			void this.drop();
		}
	};

	private release = () => {
		if (!this.ghost) {
			this.unlisten(); // a click that did not move
			this.pressed = null;
			return;
		}
		void this.drop();
	};

	private async drop() {
		const press = this.pressed;
		const ghost = this.ghost;
		if (!press || !ghost) return;
		this.unlisten();
		cancelAnimationFrame(this.frame);
		const target = this.over;
		let place = press.from;
		if (target && target !== press.from && this.onmove(press.album, target, press.from) !== false) {
			place = target;
			this.landing = `${target}|${press.album.id}`; // its card in the new place waits for the flight
			await tick();
		}
		await this.fly(ghost, press, place);
		ghost.remove();
		this.landing = null;
		this.album = null;
		this.over = null;
		this.ghost = null;
		this.pressed = null;
		document.documentElement.classList.remove('dragging');
	}

	/** The card in the hand goes to the card that is in the page now (its new place, or the old one). */
	private async fly(ghost: HTMLElement, press: NonNullable<ReleaseDrag['pressed']>, place: string) {
		// A release can stand in a category and in series at once: the card is looked for in the place it went to.
		const card = document.querySelector<HTMLElement>(
			`[data-category="${place}"] [data-album="${press.album.id}"]`
		);
		ghost.style.scale = '1';
		ghost.style.rotate = '0deg';
		ghost.style.boxShadow = '0 0 0 rgba(0, 0, 0, 0)';
		if (!card) {
			await ghost.animate([{ opacity: 1 }, { opacity: 0 }], { duration: 160, fill: 'forwards' })
				.finished;
			return;
		}
		card.scrollIntoView({ block: 'nearest', inline: 'nearest' });
		const to = card.getBoundingClientRect();
		await ghost.animate(
			[
				{ transform: ghost.style.transform || 'translate(0, 0)' },
				{ transform: `translate(${to.left - press.rect.left}px, ${to.top - press.rect.top}px)` }
			],
			{ duration: FLIGHT, easing: FLIGHT_EASING, fill: 'forwards' }
		).finished;
	}
}
