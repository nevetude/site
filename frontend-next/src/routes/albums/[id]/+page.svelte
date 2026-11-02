<script lang="ts">
	import { invalidateAll } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { api } from '#lib/api/client.js';
	import { AlbumDraft } from '#lib/features/album/album-draft.svelte.js';
	import AlbumInfo from '#lib/features/album/album-info.svelte';
	import AlbumScore from '#lib/features/album/album-score.svelte';
	import DebugData from '#lib/features/album/debug-data.svelte';
	import Descriptors from '#lib/features/album/descriptors.svelte';
	import Gallery from '#lib/features/album/gallery.svelte';
	import Credits from '#lib/features/album/credits.svelte';
	import Facts from '#lib/features/album/facts.svelte';
	import Lists from '#lib/features/album/lists.svelte';
	import Reviews from '#lib/features/album/reviews.svelte';
	import Description from '#lib/components/description.svelte';
	import CreditsEditor from '#lib/features/edit/credits-editor.svelte';
	import DescriptionEditor from '#lib/features/edit/description-editor.svelte';
	import EditBar from '#lib/features/edit/edit-bar.svelte';
	import OtherVersions from '#lib/features/album/other-versions.svelte';
	import ReleaseCard from '#lib/features/album/release-card.svelte';
	import TracklistCard from '#lib/features/album/tracklist-card.svelte';
	import Videos from '#lib/features/album/videos.svelte';
	import { artistTint, coverHint, coverList, coverTint } from '#lib/utils/albums.js';
	import TechnicalBlock from '#lib/components/technical-block.svelte';
	import ReleaseNeighbors from '#lib/features/album/release-neighbors.svelte';
	import Breadcrumbs from '#lib/components/breadcrumbs.svelte';
	import Collapse from '#lib/components/collapse.svelte';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();
	const album = $derived(data.album);
	const owner = $derived(album.artists[0]);
	const trail = $derived([
		...(owner
			? [{ label: owner.base_name, href: resolve('/artists/[id]', { id: String(owner.id) }) }]
			: []),
		{ label: album.base_name }
	]);
	const covers = $derived(coverList(album));
	// The ground of the smaller cards (the tracklist, the clips): the colour of the cover, darker than the big card.
	const tint = $derived(coverTint(album, true));
	// The tracklist and the signs of the clips: the plain grey of a panel with some of the colour of the cover in it.
	const hint = $derived(coverHint(album));
	// The names of the artists of the album, wherever they are on the page (`.artist` in `app.css`).
	const artistColor = $derived(artistTint(album));

	// The edit mode: the pencil makes a draft of the album, Save sends what differs from it, and the page is read again.
	let draft = $state<AlbumDraft | null>(null);
	let saving = $state(false);
	let error = $state('');

	async function save() {
		if (!draft) return;
		saving = true;
		error = (await draft.save()) ?? '';
		if (!error) {
			await invalidateAll();
			draft = null;
		}
		saving = false;
	}

	// The tiles of the descriptors open over the lower edge of the header (which is 360px high whatever is in it).
	// The column of the description moves down by as much as they stick out, nothing else moves.
	let playing = $state<string | null>(null); // the clip in the main place, see `Videos`
	let blocks = $state<Record<string, HTMLElement | undefined>>({}); // the blocks that move with the clips
	let tagsOpen = $state(false);
	let tagsFull = $state(0);
	let tagsBox = $state<HTMLElement | null>(null);
	let lowerRow = $state<HTMLElement | null>(null);
	let info = $state<HTMLElement | null>(null); // the header with the facts: the page is scrolled to its lower edge for a clip
	const GAP = 12;
	const push = $derived.by(() => {
		if (!tagsOpen || !tagsBox || !lowerRow) return 0;
		const out =
			tagsBox.getBoundingClientRect().top + tagsFull - lowerRow.getBoundingClientRect().top;
		return Math.max(0, out + GAP);
	});
</script>

<svelte:head><title>{album.base_name} · Music</title></svelte:head>

<div style:--artist-color={artistColor}>
	<Breadcrumbs {trail}>
		{#snippet end()}
			<ReleaseNeighbors neighbors={data.neighbors} title={album.base_name} off={draft !== null} />
		{/snippet}
	</Breadcrumbs>
	<EditBar
		editing={draft !== null}
		{saving}
		{error}
		onedit={() => {
			draft = new AlbumDraft(album, data.tracks);
			error = '';
		}}
		onsave={save}
		oncancel={() => (draft = null)}
	/>

	{#key album.id}
		{@const albumId = album.id}
		<div class="space-y-10">
			<!-- Two rows. First: the coloured square of the release and the header with the main facts. Second: the
		     tracklist with what goes under it, and the credits with the description. The first row is 360px
		     high whatever is in it, so the line under the header never moves; every cell of the second row
		     starts right under it, and the tracklist lies over the lower edge of the coloured square.
		     On a narrow screen the header comes first. -->
			<div
				class="grid grid-cols-[minmax(0,1fr)] items-start gap-x-8 gap-y-6 min-[1000px]:grid-cols-[380px_minmax(0,1fr)] min-[1000px]:gap-y-0 {draft
					? 'min-[1000px]:grid-rows-[minmax(360px,auto)_auto]'
					: 'min-[1000px]:grid-rows-[360px_auto]'}"
			>
				<div class="order-2 min-[1000px]:order-none min-[1000px]:-mb-12 min-[1000px]:self-stretch">
					<ReleaseCard {album} {covers} bind:draft />
				</div>
				<div bind:this={info} class="order-1 min-[1000px]:order-none min-[1000px]:self-stretch">
					<!-- Three rows. The first: the title with the facts of the release, and the rating. The second: Country and
				     Language. The third: Scenes and Genres, and the tiles. The rating is as high as the first two rows, so the
				     tiles under it always stand beside Scenes. The last row takes what is left, so the grey panel of the facts ends
				     exactly where the tracklist begins, whatever it holds. Under 1200px everything is one column. -->
					<div
						class="grid grid-cols-[minmax(0,1fr)] gap-y-3 pb-6 min-[1000px]:h-full min-[1200px]:grid-cols-[minmax(0,1fr)_400px] min-[1200px]:grid-rows-[auto_auto_1fr] min-[1200px]:gap-x-8 min-[1200px]:gap-y-0 min-[1200px]:pb-0"
					>
						<AlbumInfo {album} bind:draft />
						<AlbumScore />
						<Descriptors bind:open={tagsOpen} bind:full={tagsFull} bind:box={tagsBox} />
					</div>
				</div>
				<div class="relative z-10 order-3 space-y-6 min-[1000px]:order-none">
					<TracklistCard {album} tracks={data.tracks} tint={hint} bind:draft />
					{#if album.related.length}<OtherVersions related={album.related} />{/if}
					<Lists />
					{#if playing}<Reviews />{/if}
				</div>
				<!-- The lower part: two columns. On the left the credits and the reviews. On the right the description, the
			     clips under it and the gallery. With a clip in the main place the clips take both columns in the first
			     row (see `Videos`) and everything else goes down: the left column beside the description. Under 1200px
			     it is one column in the order of the page. The rows are the same in both cases: the third one takes what
			     is left, so a tall left column does not push the right one apart. -->
				<div
					bind:this={lowerRow}
					class="order-4 grid grid-cols-[minmax(0,1fr)] items-start gap-y-8 min-[1000px]:order-none min-[1200px]:grid-cols-[minmax(0,1fr)_400px] min-[1200px]:grid-rows-[auto_auto_1fr] min-[1200px]:gap-x-8 min-[1200px]:gap-y-0"
				>
					<div
						bind:this={blocks.left}
						class="space-y-8 min-[1200px]:col-start-1 {playing
							? 'min-[1200px]:row-span-2 min-[1200px]:row-start-2 min-[1200px]:mt-8'
							: 'min-[1000px]:mt-10 min-[1200px]:row-span-3 min-[1200px]:row-start-1'}"
					>
						{#if draft}
							<CreditsEditor bind:credits={draft.credits} />
						{:else if album.credits.length}
							<Collapse fade="var(--background)">
								<Credits groups={album.credits} main={album.artists} />
							</Collapse>
						{/if}
						{#if !playing}
							<Reviews />
							<Facts />
						{/if}
					</div>
					{#if draft || album.description}
						<div
							bind:this={blocks.description}
							class="transition-[margin] duration-200 ease-out min-[1200px]:col-start-2 {playing
								? 'min-[1200px]:row-start-2 min-[1200px]:mt-8'
								: 'min-[1200px]:row-start-1'}"
							style:margin-top={playing || !push ? undefined : `${push}px`}
						>
							{#if draft}
								<DescriptionEditor
									bind:value={draft.description}
									edited={draft.edited('description')}
									bind:reset={draft.reset.description}
								/>
							{:else}
								<Collapse fade="var(--card)" class="rounded-xl">
									<Description
										dom={album.description_dom}
										text={album.description ?? ''}
										refs={album.description_refs}
									/>
								</Collapse>
							{/if}
						</div>
					{/if}
					<Videos
						videos={data.videos}
						tracks={data.tracks}
						tint={hint}
						main={album.artists}
						bind:playing
						others={() => Object.values(blocks)}
						top={() => info}
						push={playing ? push : 0}
						class={playing
							? 'min-[1200px]:col-span-2 min-[1200px]:col-start-1 min-[1200px]:row-start-1 min-[1200px]:mt-8'
							: album.description
								? 'min-[1200px]:col-start-2 min-[1200px]:row-start-2 min-[1200px]:mt-8'
								: 'min-[1200px]:col-start-2 min-[1200px]:row-start-1'}
					/>
					<div
						bind:this={blocks.gallery}
						class="space-y-8 min-[1200px]:col-start-2 min-[1200px]:row-start-3 min-[1200px]:mt-8"
					>
						<Gallery {tint} />
						{#if playing}<Facts />{/if}
					</div>
				</div>
			</div>
			<TechnicalBlock
				subject="album"
				entity={album}
				fetchRaw={async () =>
					(
						await api.GET('/api/v1/albums/{album_id}/raw', {
							params: { path: { album_id: albumId } }
						})
					).data}
			>
				<DebugData {album} />
			</TechnicalBlock>
		</div>
	{/key}
</div>
