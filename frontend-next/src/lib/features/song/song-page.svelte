<script lang="ts">
	import { invalidateAll } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { api } from '#lib/api/client.js';
	import type { Lyrics, SongDetail } from '#lib/api/client.js';
	import AlbumScore from '#lib/features/album/album-score.svelte';
	import Credits from '#lib/features/album/credits.svelte';
	import DebugData from '#lib/features/album/debug-data.svelte';
	import Descriptors from '#lib/features/album/descriptors.svelte';
	import Facts from '#lib/features/album/facts.svelte';
	import Gallery from '#lib/features/album/gallery.svelte';
	import Lists from '#lib/features/album/lists.svelte';
	import ReleaseCard from '#lib/features/album/release-card.svelte';
	import Reviews from '#lib/features/album/reviews.svelte';
	import { artistTint, coverHint, coverList, coverTint } from '#lib/utils/albums.js';
	import Description from '#lib/components/description.svelte';
	import TechnicalBlock from '#lib/components/technical-block.svelte';
	import AppearsOn from '#lib/features/song/appears-on.svelte';
	import LyricsCard from '#lib/features/song/lyrics-card.svelte';
	import RelatedSongs from '#lib/features/song/related-songs.svelte';
	import SongClips from '#lib/features/song/song-clips.svelte';
	import SongInfo from '#lib/features/song/song-info.svelte';
	import { songCredits, songVideos } from '#lib/features/song/song.js';
	import Breadcrumbs from '#lib/components/breadcrumbs.svelte';
	import Collapse from '#lib/components/collapse.svelte';
	import CreditsEditor from '#lib/features/edit/credits-editor.svelte';
	import DescriptionEditor from '#lib/features/edit/description-editor.svelte';
	import EditBar from '#lib/features/edit/edit-bar.svelte';
	import { SongDraft } from '#lib/features/song/song-draft.svelte.js';

	// Three columns. On the left the cover, under it the clip of the song, then "Appears on", the related songs and the
	// lists. In the middle the card of the lyrics (the title and the artists are its top), and under it the reviews. On
	// the right the rating, the description, the main facts, the credits, the gallery and the tiles of the tags. A clip
	// is played in its own tile (see `SongClips`); nothing else moves.
	// `albumId`: the album the visitor came through, if any: it stands in the breadcrumbs between the artist and the song.
	type Props = { song: SongDetail; lyrics: Lyrics | null; albumId: number | null };

	let { song, lyrics, albumId }: Props = $props();

	const owner = $derived(song.artists[0]);
	const via = $derived(song.albums.find((placement) => placement.album.id === albumId)?.album);
	const trail = $derived([
		...(owner
			? [{ label: owner.base_name, href: resolve('/artists/[id]', { id: String(owner.id) }) }]
			: []),
		...(via
			? [{ label: via.base_name, href: resolve('/albums/[id]', { id: String(via.id) }) }]
			: []),
		{ label: song.base_name }
	]);
	const covers = $derived(coverList({ ...song, covers: [] }));
	const tint = $derived(coverTint(song, true));
	const hint = $derived(coverHint(song));
	const artistColor = $derived(artistTint(song));
	const credits = $derived(songCredits(song));
	const videos = $derived(songVideos(song));

	// The edit mode: the pencil makes a draft of the song, Save sends what differs from it, and the page is read again.
	let draft = $state<SongDraft | null>(null);
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
</script>

<svelte:head><title>{song.base_name} · Music</title></svelte:head>

<div style:--artist-color={artistColor}>
	<Breadcrumbs {trail} />
	<EditBar
		editing={draft !== null}
		{saving}
		{error}
		onedit={() => {
			draft = new SongDraft(song);
			error = '';
		}}
		onsave={save}
		oncancel={() => (draft = null)}
	/>

	{#key song.id}
		<div class="space-y-10">
			<!-- One grid for all the blocks. The middle column is as wide as the lyrics (22.75rem at the least, 29.75rem at the most)
			     and the right one takes what is left (12.25rem at the least). Under 1200px it is two columns, under 1000px one: the
			     lyrics (the title is their top) come first. Nothing on the page moves while the clip is played. -->
			<div
				class="grid grid-cols-[minmax(0,1fr)] items-start gap-x-8 gap-y-6 min-[1000px]:grid-cols-[380px_minmax(0,1fr)] min-[1200px]:grid-cols-[380px_minmax(22.75rem,max-content)_minmax(12.25rem,1fr)] min-[1200px]:grid-rows-[auto_1fr]"
			>
				<div
					class="order-2 space-y-6 min-[1000px]:order-none min-[1000px]:col-start-1 min-[1000px]:row-start-1 min-[1000px]:row-end-4 min-[1200px]:row-end-3"
				>
					<SongClips {song} {videos} tint={hint}>
						{#snippet cover(pulled)}
							<div class="mb-3 {pulled ? 'min-[1000px]:-mb-12' : ''}">
								<ReleaseCard album={song} {covers} bind:draft />
							</div>
						{/snippet}
					</SongClips>
					{#if song.albums.length}<AppearsOn albums={song.albums} />{/if}
					{#if song.related.length}<RelatedSongs related={song.related} />{/if}
					<Lists />
				</div>

				<div
					class="order-1 min-w-0 min-[1000px]:order-none min-[1000px]:col-start-2 min-[1000px]:row-start-1 min-[1200px]:max-w-[29.75rem]"
				>
					<LyricsCard {song} {lyrics} tint={hint} bind:draft />
				</div>

				<div
					class="order-3 min-w-0 space-y-6 min-[1000px]:order-none min-[1000px]:col-start-2 min-[1000px]:row-start-2"
				>
					<Reviews />
					<Facts />
				</div>

				<div
					class="order-4 min-w-0 space-y-6 min-[1000px]:order-none min-[1000px]:col-start-2 min-[1000px]:row-start-3 min-[1200px]:col-start-3 min-[1200px]:row-start-1 min-[1200px]:row-end-3"
				>
					<AlbumScore class="h-40" />
					{#if draft}
						<DescriptionEditor
							bind:value={draft.description}
							edited={draft.edited('description')}
							bind:reset={draft.reset.description}
						/>
					{:else if song.description}
						<Collapse fade="var(--card)" class="rounded-xl">
							<Description
								dom={song.description_dom}
								text={song.description}
								refs={song.description_refs}
							/>
						</Collapse>
					{/if}
					<SongInfo {song} bind:draft />
					{#if draft}
						<CreditsEditor bind:credits={draft.credits} />
					{:else if credits.length}
						<Collapse fade="var(--background)">
							<Credits groups={credits} main={song.artists} />
						</Collapse>
					{/if}
					<Gallery {tint} class="gap-1.5" />
					<Descriptors words={song.tags} />
				</div>
			</div>
			<TechnicalBlock
				subject="song"
				entity={song}
				fetchRaw={async () =>
					(
						await api.GET('/api/v1/songs/{song_id}/raw', {
							params: { path: { song_id: song.id } }
						})
					).data}
			>
				<DebugData album={song} />
			</TechnicalBlock>
		</div>
	{/key}
</div>
