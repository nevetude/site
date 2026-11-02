<script lang="ts">
	import CoverPlaceholder from '#lib/components/cover-placeholder.svelte';
	import ExplicitEye from '#lib/components/explicit-eye.svelte';
	import CalendarOff from '@lucide/svelte/icons/calendar-off';
	import PanelTop from '@lucide/svelte/icons/panel-top';
	import { resolve } from '$app/paths';
	import type { ArtistAlbum } from '#lib/api/client.js';
	import { isDefaultCover } from '#lib/utils/albums.js';
	import { formatCount, formatFullDate, formatRelease } from '#lib/utils/format.js';
	import CommaList from '#lib/components/comma-list.svelte';

	// `note` is a third line under the artists of a grid card (how the album is related to the one on the page).
	type Props = {
		album: ArtistAlbum;
		layout?: 'grid' | 'list';
		height: number;
		cover: number;
		note?: string;
		showViews?: boolean; // the views of the songs of the album, in the place of the date
		editing?: boolean; // a card of the edit mode: it is taken and carried, not followed
		markUnreleased?: boolean; // the sign of an album that is not out yet (the page of an artist)
	};

	let {
		album,
		layout = 'grid',
		height,
		cover,
		note,
		showViews = false,
		editing = false,
		markUnreleased = false
	}: Props = $props();

	const year = $derived(formatRelease(album.release_date, 'year'));
	// Credited only (a remix, a production): nobody is listed on the album, so show the artist's roles.
	const byline = $derived(album.artists.length ? album.artists : [...album.roles].sort());
	const labels = $derived(album.labels);
	const fullDate = $derived(formatFullDate(album.release_date, album.release_date_precision));
	const tracks = $derived(`${album.tracks_count} ${album.tracks_count === 1 ? 'Track' : 'Tracks'}`);
	// Hovering the name shows the whole title with the addition in brackets; the icon shows only the addition.
	const tip = $derived(album.variant ? `${album.base_name} (${album.variant})` : album.base_name);

	const list = $derived(layout === 'list');
</script>

{#snippet title()}
	<!-- The addition to the title (Live, Deluxe, ...) stays as text of the same size, darker, and the icon marks it. -->
	<span
		class="min-w-0 flex-1 text-[13px] leading-5 font-medium {list ? 'line-clamp-2' : 'truncate'}"
		title={tip}
	>
		{album.base_name}
		{#if album.variant}<span class="font-normal text-subtle">{album.variant}</span>{/if}
	</span>
	{#if album.variant}
		<span title={album.variant} class="shrink-0 text-subtle">
			<PanelTop class="size-4" aria-label={album.variant} />
		</span>
	{/if}
	<!-- An album that is not out yet has the sign of a calendar with no date, at the end of the line like the sign of an addition. -->
	{#if markUnreleased && album.is_released === false}
		<span title="Unreleased" class="shrink-0 text-subtle">
			<CalendarOff class="size-4" aria-label="Unreleased" />
		</span>
	{/if}
{/snippet}

<svelte:element
	this={editing ? 'div' : 'a'}
	href={editing ? undefined : resolve('/albums/[id]', { id: String(album.id) })}
	style:height="{height}px"
	style:transition="height 200ms ease-out, color 150ms ease-out"
	class="group/card flex overflow-hidden rounded-lg p-3 text-left text-foreground hover:bg-accent hover:text-white {list
		? ''
		: 'flex-col items-stretch gap-1'}"
>
	<!-- The rows view stands where two cards of the grid stood, with the same padding around it. -->
	<div
		class={list ? 'flex min-w-0 flex-1 overflow-hidden rounded-lg' : 'contents'}
		style:height={list ? `${cover}px` : undefined}
	>
		<!-- In the rows view the cover has its size in px, whatever the card height is doing: when the
		     height eases between the views the cover is cut off below, never squeezed. -->
		<div
			class="relative overflow-hidden bg-background {list
				? 'shrink-0'
				: 'aspect-square w-full rounded-lg'}"
			style:width={list ? `${cover}px` : undefined}
			style:height={list ? `${cover}px` : undefined}
		>
			{#if isDefaultCover(album.cover_thumbnail_url)}
				<CoverPlaceholder class="size-1/4 max-w-10" />
			{:else if album.cover_thumbnail_url}
				<img
					src={album.cover_thumbnail_url}
					alt=""
					loading="lazy"
					decoding="async"
					class="block size-full object-cover {album.cover_explicit ? 'scale-110 blur-xs' : ''}"
				/>
				{#if album.cover_explicit}<ExplicitEye class="group-hover/card:text-white/90" />{/if}
			{/if}
		</div>

		{#if !list}
			<div class="flex items-start gap-1.5">{@render title()}</div>
			<div class="flex items-baseline justify-between gap-2 text-xs leading-4 text-subtle">
				<span class="truncate"><CommaList items={byline} wrap={false} /></span>
				{#if showViews}
					{#if album.view_count}
						<span class="tabular-nums shrink-0" title="Views of the songs"
							>{formatCount(album.view_count)}</span
						>
					{/if}
				{:else if year}
					<span class="tabular-nums shrink-0">{year}</span>
				{/if}
			</div>
			{#if note}<div class="truncate text-left text-xs leading-4 text-subtle">
					{note}
				</div>{/if}
		{:else}
			<!-- A rectangle that continues the cover, on a darker ground that lights up on hover. The card is only as tall as
			     the cover: a long title or many artists are cut short and never make it taller. -->
			<div
				class="flex min-w-0 flex-1 flex-col gap-1 bg-background px-3 py-2.5 group-hover/card:bg-muted"
			>
				<div class="flex items-start gap-1.5">{@render title()}</div>
				<div class="truncate text-[11px] text-muted-foreground" title={byline.join(', ')}>
					<CommaList items={byline} wrap={false} />
				</div>
				{#if labels.length}
					<div class="truncate text-[11px] text-subtle" title={labels.join(', ')}>
						<CommaList items={labels} wrap={false} />
					</div>
				{/if}
				<div class="tabular-nums mt-auto shrink-0 text-[11px] leading-snug text-subtle">
					<!-- With the sort by views the views stand in the place of the date. -->
					<div>
						{#if showViews}
							{album.view_count ? `${formatCount(album.view_count)} views` : 'No views'}
						{:else}
							{fullDate ?? 'No date'}
						{/if}
					</div>
					{#if album.tracks_count}<div>{tracks}</div>{/if}
					{#if album.import_state === 'stub'}<div>Stub</div>{/if}
				</div>
			</div>
		{/if}
	</div>
</svelte:element>
