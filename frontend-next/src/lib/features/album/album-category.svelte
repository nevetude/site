<script lang="ts">
	import ChevronDown from '@lucide/svelte/icons/chevron-down';
	import ChevronLeft from '@lucide/svelte/icons/chevron-left';
	import ChevronRight from '@lucide/svelte/icons/chevron-right';
	import X from '@lucide/svelte/icons/x';
	import { tick } from 'svelte';
	import { flip } from 'svelte/animate';
	import type { ArtistAlbum } from '#lib/api/client.js';
	import AlbumCard from '#lib/features/album/album-card.svelte';
	import type { ReleaseDrag } from '#lib/features/artist/release-drag.svelte.js';
	import { watchWidth } from '#lib/utils/watch-size.js';
	import { cardSpan, cardHeight, cellsPerRow, coverSize, perRow } from '#lib/utils/albums.js';

	type Props = {
		title?: string; // none: only the controls of the strip
		albums: ArtistAlbum[];
		view: 'grid' | 'list';
		openAll: boolean; // every category follows this; a click on the title still opens just one
		startOpen?: boolean; // open from the start, as if the chevron was pressed; it can still be closed
		resetKey: string; // a new key (another order or role) starts the strip from its beginning
		columns?: number; // cards per row of the grid view, when the place decides it and not the width
		note?: string; // a third line on every card of the grid view
		showViews?: boolean; // the views of the album on its card, in the place of the date (the list is sorted by them)
		markUnreleased?: boolean; // the cards show the sign of an album that is not out yet
		scrollEnd?: number; // a new number scrolls the strip to its end, if it has an album that is not out yet
		type?: string; // the kind of release the category is, for the edit mode: a card is dropped on it
		remove?: (album: ArtistAlbum) => void; // the edit mode of a series: a cross on every card takes it out
		drag?: ReleaseDrag | null; // the edit mode: the cards are taken and carried, and an empty place stands first
	};

	let {
		title,
		albums,
		view,
		openAll,
		startOpen = false,
		resetKey,
		columns,
		note,
		showViews = false,
		type,
		scrollEnd = 0,
		markUnreleased = false,
		remove,
		drag = null
	}: Props = $props();

	let expanded = $derived(startOpen || openAll);
	let scroller = $state<HTMLElement | null>(null);
	let track = $state<HTMLElement | null>(null);
	let width = $state(0); // the width of the strip, which is the same open or closed
	let offset = $state(0); // how far the strip is scrolled, in percent of its length

	// Closed, the strip is one row that scrolls sideways; open, the same cards wrap into rows. Both take
	// the number of cards per row and the gap from the same place, so opening never resizes a card.
	const cells = $derived(columns ?? cellsPerRow(width));
	const perView = $derived(perRow(width, view, cells));
	// A card is `span` cells wide; the cell is a share of the row.
	const cardWidth = $derived(`calc(${cardSpan(width, view, cells) * 100}% / ${cells})`);
	// Everything fits in one row: there is nothing to scroll and nothing more to open.
	const fits = $derived(albums.length <= perView);
	// A release is being carried and this category would take it.
	const receiving = $derived(!!drag && drag.over === type && drag.from !== type);
	const height = $derived(cardHeight(width, view, cells, !!note));
	const scrolls = $derived(!expanded && !fits);

	// A new order starts the strip from its beginning. Without this the browser keeps the album that was
	// first in view in sight and carries the strip along with it. Showing or hiding the unreleased
	// albums is not a new order: the strip stays where it was.
	$effect(() => {
		void resetKey;
		if (scroller) scroller.scrollLeft = 0;
	});

	let seenEnd: number | undefined; // the number the first time it is read is not a request
	$effect(() => {
		const previous = seenEnd;
		seenEnd = scrollEnd;
		if (previous === undefined || previous === scrollEnd) return;
		if (!albums.some((album) => album.is_released === false)) return;
		void tick().then(() => scroller?.scrollTo({ left: scroller.scrollWidth, behavior: 'smooth' }));
	});

	const onscroll = () => scroller && (offset = (scroller.scrollLeft / scroller.scrollWidth) * 100);
	const scrollBy = (direction: 1 | -1) =>
		scroller?.scrollBy({ left: direction * scroller.clientWidth });

	// The wheel over the strip, or over the bar above it, moves the albums sideways, and the page stays
	// where it is even at the ends.
	function wheel(node: HTMLElement) {
		const onWheel = (event: WheelEvent) => {
			if (!scrolls || !scroller) return;
			event.preventDefault();
			scroller.scrollLeft += event.deltaY + event.deltaX;
		};
		node.addEventListener('wheel', onWheel, { passive: false });
		return { destroy: () => node.removeEventListener('wheel', onWheel) };
	}

	// A click on the track, or a drag along it, puts the middle of the visible part where the pointer is.
	function seek(event: PointerEvent) {
		if (!scroller || !track) return;
		const box = track.getBoundingClientRect();
		const fraction = (event.clientX - box.left) / box.width;
		scroller.scrollLeft = fraction * scroller.scrollWidth - scroller.clientWidth / 2;
	}

	function grab(event: PointerEvent) {
		(event.currentTarget as HTMLElement).setPointerCapture(event.pointerId);
		seek(event);
	}

	const ARROW =
		'flex size-6 shrink-0 items-center justify-center rounded-md text-muted-foreground hover:bg-accent hover:text-foreground';
</script>

<!-- In the edit mode the category takes a card that is dropped on it: the strip of its releases lights up while one is over
     it; a category with no releases is only its header, and the header lights up. -->
<!-- In the edit mode an empty category is a tall target with no gap around it: empty ones stand against each other. -->
<section
	class="group/category space-y-1 {drag && !albums.length ? 'my-0' : ''}"
	data-category={drag ? type : undefined}
>
	<!-- Without a title the header is only the controls of the strip: nothing to show while everything fits. -->
	<header
		class="flex items-center gap-3 pl-3 {drag && !albums.length
			? 'h-14 rounded-lg pr-2 transition-colors duration-200'
			: ''} {drag && !albums.length && receiving ? 'bg-foreground/10' : ''}"
		class:hidden={!title && !scrolls}
	>
		{#if fits}
			<h3
				class="flex h-6 items-center text-sm font-medium text-foreground"
				title="{albums.length} releases"
			>
				{title}
			</h3>
		{:else}
			<!-- The name opens and closes the category; the tooltip says how many releases are in it. -->
			<button
				type="button"
				aria-expanded={expanded}
				title="{expanded ? 'Hide' : 'Show'} {albums.length}"
				class="group/title flex h-6 shrink-0 items-center gap-1.5 pr-2 text-foreground hover:text-white"
				onclick={() => (expanded = !expanded)}
			>
				<h3 class="text-sm font-medium">{title}</h3>
				<!-- The chevron lights up with the name: the pointer on either of them is the pointer on the button. -->
				{#if expanded}<ChevronDown
						class="size-4 text-muted-foreground group-hover/title:text-white"
					/>{:else}<ChevronRight
						class="size-4 text-muted-foreground group-hover/title:text-white"
					/>{/if}
			</button>
		{/if}

		{#if scrolls}
			<!-- Beside the name, invisible until the pointer is over the category: the position, then the arrows.
			     The whole height of the position is a zone of its own: a click puts the strip there, the wheel moves it. -->
			<div
				class="flex min-w-0 flex-1 items-center opacity-0 group-hover/category:opacity-100 focus-within:opacity-100"
			>
				<!-- svelte-ignore a11y_no_static_element_interactions -->
				<div
					bind:this={track}
					use:wheel
					class="flex h-6 min-w-0 flex-1 cursor-pointer items-center"
					onpointerdown={grab}
					onpointermove={(event) => event.buttons === 1 && seek(event)}
				>
					<div class="relative h-2 w-full rounded-full bg-accent">
						<div
							class="absolute inset-y-0 rounded-full bg-foreground/40"
							style:left="{offset}%"
							style:width="{(perView / albums.length) * 100}%"
						></div>
					</div>
				</div>
				<!-- A gap from the bar, so a click that misses the arrow does not land on the bar. -->
				<div class="ml-3 flex shrink-0 items-center">
					<button type="button" class={ARROW} aria-label="Scroll left" onclick={() => scrollBy(-1)}>
						<ChevronLeft class="size-4" />
					</button>
					<button type="button" class={ARROW} aria-label="Scroll right" onclick={() => scrollBy(1)}>
						<ChevronRight class="size-4" />
					</button>
				</div>
			</div>
		{/if}
	</header>

	{#if albums.length || !drag}
		<div
			bind:this={scroller}
			use:watchWidth={(w) => (width = w)}
			use:wheel
			{onscroll}
			class="grid rounded-xl transition-colors duration-200 [overflow-anchor:none] {receiving
				? 'bg-foreground/10'
				: ''} {expanded
				? ''
				: 'grid-flow-col overflow-x-auto overscroll-x-contain [scrollbar-width:none]'}"
			style:grid-template-columns={expanded ? `repeat(${perView}, ${cardWidth})` : undefined}
			style:grid-auto-columns={expanded ? undefined : cardWidth}
		>
			{#each albums as album (album.id)}
				<!-- The box moves when the cards around it come and go (`flip`); in the edit mode it is taken with a press. -->
				<!-- svelte-ignore a11y_no_static_element_interactions -->
				<div
					animate:flip={{ duration: 260 }}
					data-album={drag ? album.id : undefined}
					class="group/pick relative min-w-0 transition-opacity duration-200 {drag
						? 'cursor-grab touch-none select-none'
						: ''} {drag?.landing === `${type}|${album.id}`
						? 'opacity-0'
						: drag?.album?.id === album.id && drag.from === type
							? 'opacity-30'
							: ''}"
					ondragstart={drag ? (event) => event.preventDefault() : undefined}
					onpointerdown={drag && type
						? (event) => drag.press(event, album, type, event.currentTarget)
						: undefined}
				>
					<AlbumCard
						{album}
						layout={view}
						{height}
						{note}
						{showViews}
						editing={!!drag}
						{markUnreleased}
						cover={coverSize(width, cells)}
					/>
					{#if remove}
						<button
							type="button"
							aria-label="Take out of the series"
							title="Take out of the series"
							class="absolute top-4 right-4 flex size-6 items-center justify-center rounded-md bg-background/80 text-muted-foreground opacity-0 group-hover/pick:opacity-100 hover:bg-destructive/20 hover:text-destructive focus-visible:opacity-100"
							onpointerdown={(event) => event.stopPropagation()}
							onclick={() => remove(album)}
						>
							<X class="size-4" />
						</button>
					{/if}
				</div>
			{/each}
		</div>
	{/if}
</section>
