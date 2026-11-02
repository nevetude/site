<script lang="ts">
	import { invalidateAll } from '$app/navigation';
	import { api } from '#lib/api/client.js';
	import { ArtistDraft } from '#lib/features/artist/artist-draft.svelte.js';
	import DescriptionEditor from '#lib/features/edit/description-editor.svelte';
	import EditBar from '#lib/features/edit/edit-bar.svelte';
	import NamesEditor from '#lib/features/artist/names-editor.svelte';
	import MembersEditor from '#lib/features/artist/members-editor.svelte';
	import AlbumGrid from '#lib/features/artist/album-grid.svelte';
	import ArtistGenres from '#lib/features/artist/artist-genres.svelte';
	import ArtistInfo from '#lib/features/artist/artist-info.svelte';
	import ArtistPortrait from '#lib/features/artist/artist-portrait.svelte';
	import ArtistVideos from '#lib/features/artist/artist-videos.svelte';
	import Description from '#lib/components/description.svelte';
	import TechnicalBlock from '#lib/components/technical-block.svelte';
	import RelatedArtists from '#lib/features/artist/related-artists.svelte';
	import ProfileLinks from '#lib/features/artist/profile-links.svelte';
	import SongList from '#lib/features/artist/song-list.svelte';
	import TopTracks from '#lib/features/artist/top-tracks.svelte';
	import Breadcrumbs from '#lib/components/breadcrumbs.svelte';
	import Collapse from '#lib/components/collapse.svelte';
	import { watchHeight } from '#lib/utils/watch-size.js';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();
	const artist = $derived(data.artist);

	// From 1000px the popular tracks and the column of the groups and the description stand side by side, and the
	// column must not end lower than the tracks: the description is as high as is left under the groups.
	let width = $state(0);
	let tracksHeight = $state(0);
	let groupsHeight = $state(0);
	const GAP = 32; // the space-y-8 between the blocks of the column
	const descriptionHeight = $derived(
		width >= 1000 && tracksHeight
			? Math.max(160, tracksHeight - (artist.groups.length ? groupsHeight + GAP : 0))
			: undefined
	);

	// The edit mode: the pencil makes a draft of the artist, Save sends what differs from it, and the page is read again.
	let draft = $state<ArtistDraft | null>(null);
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

<svelte:window bind:innerWidth={width} />
<svelte:head><title>{artist.base_name} · Music</title></svelte:head>

<Breadcrumbs trail={[{ label: artist.base_name }]} />
<EditBar
	editing={draft !== null}
	{saving}
	{error}
	onedit={() => {
		draft = new ArtistDraft(artist);
		error = '';
	}}
	onsave={save}
	oncancel={() => (draft = null)}
/>

{#key artist.id}
	{@const artistId = artist.id}
	<div class="space-y-10">
		<!-- The top of the page is laid out like the top of the page of an album. Two rows. First: the portrait in its panel
		     and the header with the facts. Second: the popular tracks with what goes under them, and the description with the
		     links and the members beside it. The header is 360px high at least; the popular tracks lie over the lower edge of
		     the panel of the portrait. On a narrow screen the header comes first. -->
		<div
			class="grid grid-cols-[minmax(0,1fr)] items-start gap-x-8 gap-y-6 min-[1000px]:grid-cols-[380px_minmax(0,1fr)] min-[1000px]:grid-rows-[minmax(360px,auto)_auto] min-[1000px]:gap-y-0"
		>
			<div class="order-2 min-[1000px]:order-none min-[1000px]:-mb-12 min-[1000px]:self-stretch">
				<ArtistPortrait
					src={artist.cover_url}
					name={artist.base_name}
					verified={artist.is_verified}
					bind:draft
				/>
			</div>
			<div class="order-1 min-[1000px]:order-none min-[1000px]:self-stretch">
				<!-- The same panel as on the page of an album, as wide as there: the right column stays for the genres. It is as
				     high as the row, so its lower edge is where the popular tracks begin. -->
				<div
					class="grid grid-cols-[minmax(0,1fr)] gap-y-3 min-[1000px]:h-full min-[1200px]:grid-cols-[minmax(0,1fr)_400px] min-[1200px]:gap-x-8"
				>
					<div class="min-w-0 rounded-xl bg-card px-4 pt-4">
						<ArtistInfo {artist} bind:draft />
					</div>
					{#if !draft}
						<div class="min-w-0 min-[1200px]:self-start">
							<ArtistGenres genres={artist.genres} />
						</div>
					{/if}
				</div>
			</div>
			<div
				use:watchHeight={(h) => (tracksHeight = h)}
				class="relative z-10 order-3 min-[1000px]:order-none"
			>
				{#if draft}
					<!-- Nothing of the popular tracks is edited here: the names of the artist stand in their place. -->
					<section class="rounded-xl bg-card px-4 pt-4">
						<NamesEditor bind:draft artistId={artist.id} />
					</section>
				{:else}
					<TopTracks
						artistId={artist.id}
						ownSongs={artist.song_roles.some(({ role }) => role === 'Artist')}
					/>
				{/if}
			</div>
			<div
				class="order-4 grid grid-cols-[minmax(0,1fr)] items-start gap-y-8 min-[1000px]:order-none min-[1200px]:grid-cols-[minmax(0,1fr)_400px] min-[1200px]:gap-x-8"
			>
				<!-- A group shows its members first, in the place of the description, and the description under them. -->
				<div class="min-w-0 space-y-8">
					{#if !draft && artist.groups.length}
						<div use:watchHeight={(h) => (groupsHeight = h)}>
							<RelatedArtists title="Member of" artists={artist.groups} />
						</div>
					{/if}
					{#if !draft}<RelatedArtists title="Members" artists={artist.members} />{/if}
					{#if draft && (draft.artistType === 'group' || draft.members.length)}
						<MembersEditor bind:draft artistId={artist.id} />
					{/if}
					{#if draft}
						<DescriptionEditor
							bind:value={draft.description}
							edited={draft.edited('description')}
							bind:reset={draft.reset.description}
						/>
					{:else if artist.description}
						<Collapse fade="var(--card)" class="rounded-xl" height={descriptionHeight}>
							<Description
								dom={artist.description_dom}
								text={artist.description}
								refs={artist.description_refs}
							/>
						</Collapse>
					{/if}
				</div>
				{#if !draft}
					<div class="min-w-0 space-y-8">
						<ProfileLinks links={artist.links} />
					</div>
				{/if}
			</div>
		</div>

		<AlbumGrid artistId={artist.id} roles={artist.album_roles} series={artist.series} bind:draft />
		{#if !draft}
			<ArtistVideos artistId={artist.id} />
			<SongList artistId={artist.id} roles={artist.song_roles} />
			<TechnicalBlock
				subject="artist"
				entity={artist}
				fetchRaw={async () =>
					(
						await api.GET('/api/v1/artists/{artist_id}/raw', {
							params: { path: { artist_id: artistId } }
						})
					).data}
			/>
		{/if}
	</div>
{/key}
