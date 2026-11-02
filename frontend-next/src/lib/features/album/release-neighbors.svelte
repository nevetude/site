<script lang="ts">
	import ChevronLeft from '@lucide/svelte/icons/chevron-left';
	import ChevronRight from '@lucide/svelte/icons/chevron-right';
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import CoverPlaceholder from '#lib/components/cover-placeholder.svelte';
	import { isDefaultCover } from '#lib/utils/albums.js';
	import type { AlbumNeighbors } from '#lib/api/client.js';

	// The line of the page, on its right: the newer album of the artist on the left, this one, and the older one on
	// the right, in the look of the breadcrumbs. The arrows of the keyboard go the same way.
	let {
		neighbors,
		title,
		off = false
	}: { neighbors: AlbumNeighbors; title: string; off?: boolean } = $props();

	const { previous, next } = $derived(neighbors);
	const link = (id: number) => resolve('/albums/[id]', { id: String(id) });

	// Not while something is typed, in a player or in a menu, and not with a key held for something else.
	function key(event: KeyboardEvent) {
		if (off || event.defaultPrevented || event.altKey || event.ctrlKey || event.metaKey) return;
		const target = event.target as HTMLElement;
		if (
			target.closest(
				'input, textarea, select, iframe, [contenteditable], [role=menu], [role=listbox]'
			)
		)
			return;
		const to = event.key === 'ArrowLeft' ? next : event.key === 'ArrowRight' ? previous : null;
		if (to) void goto(link(to.id));
	}
</script>

<svelte:window onkeydown={key} />

<!-- A small cover: only blurred (there is no room for the eye); with no cover of its own, a grey box. -->
{#snippet cover(album: NonNullable<typeof previous>)}
	<span class="relative size-5 shrink-0 overflow-hidden rounded-sm">
		{#if isDefaultCover(album.cover_thumbnail_url)}
			<CoverPlaceholder class="size-3" />
		{:else}
			<img
				src={album.cover_thumbnail_url}
				alt=""
				class="size-full object-cover {album.cover_explicit ? 'scale-110 blur-xs' : ''}"
			/>
		{/if}
	</span>
{/snippet}

{#snippet side(album: NonNullable<typeof previous>, backwards: boolean)}
	<a
		href={link(album.id)}
		title="{album.base_name}{album.variant ? ` ${album.variant}` : ''}"
		class="flex min-w-0 items-center gap-1.5 transition-colors hover:text-foreground {backwards
			? ''
			: 'justify-end'}"
	>
		{#if backwards && album.cover_thumbnail_url}
			{@render cover(album)}
		{/if}
		<span class="truncate">{album.base_name}</span>
		{#if !backwards && album.cover_thumbnail_url}
			{@render cover(album)}
		{/if}
	</a>
{/snippet}

<!-- Five places in a block as wide as the rating beside it (400px), so that this album stays in the middle whatever the neighbors are called: a neighbor is
     pressed to the outer edge of its place and a long name is cut; the arrows stand between them and the album. The newer album is on the left, the older on the right. A place
     with no neighbor is left empty. -->
<nav
	aria-label="Releases of the artist"
	class="grid w-[400px] max-w-full grid-cols-[minmax(0,1fr)_auto_minmax(0,1.2fr)_auto_minmax(0,1fr)] items-center gap-2 text-sm text-muted-foreground"
>
	<div class="flex min-w-0">
		{#if next}{@render side(next, true)}{/if}
	</div>
	<ChevronLeft class="size-3.5 {next ? '' : 'invisible'}" />
	<span class="truncate text-center text-foreground" {title}>{title}</span>
	<ChevronRight class="size-3.5 {previous ? '' : 'invisible'}" />
	<div class="flex min-w-0 justify-end">
		{#if previous}{@render side(previous, false)}{/if}
	</div>
</nav>
