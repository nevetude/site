<script lang="ts">
	import { resolve } from '$app/paths';
	import type { AlbumDetail } from '#lib/api/client.js';
	import { languageName } from '#lib/utils/albums.js';
	import { formatFullDate } from '#lib/utils/format.js';
	import FactRow from '#lib/components/fact-row.svelte';
	import Plus from '@lucide/svelte/icons/plus';
	import X from '@lucide/svelte/icons/x';
	import { Badge } from '#lib/components/ui/badge/index.js';
	import { Button } from '#lib/components/ui/button/index.js';
	import ArtistPick from '#lib/features/edit/artist-pick.svelte';
	import type { AlbumDraft } from '#lib/features/album/album-draft.svelte.js';
	import DateField from '#lib/features/edit/date-field.svelte';
	import SelectField from '#lib/features/edit/select-field.svelte';
	import TitleFields from '#lib/features/edit/title-fields.svelte';
	import ClampList from '#lib/components/clamp-list.svelte';
	import CommaList from '#lib/components/comma-list.svelte';
	import ArtistLinks from '#lib/components/artist-links.svelte';
	import EntityTitle from '#lib/components/entity-title.svelte';

	// `draft`: the page is being edited, and the title and the facts that can be changed are fields.
	let { album, draft = $bindable(null) }: { album: AlbumDetail; draft?: AlbumDraft | null } =
		$props();

	// An abbreviation and a name of two words are written by hand; any other type is a word with a capital letter.
	const TYPE_NAMES: Record<string, string> = { ep: 'EP', dj_mix: 'DJ mix' };
	const typeName = (type: string) => TYPE_NAMES[type] ?? type[0].toUpperCase() + type.slice(1);

	const TYPES = [
		{ value: '', label: '—' },
		...[
			'album',
			'ep',
			'single',
			'compilation',
			'live',
			'mixtape',
			'soundtrack',
			'dj_mix',
			'other'
		].map((value) => ({ value, label: typeName(value) }))
	];
	const STATUSES = [
		{ value: '', label: 'Status: —' },
		{ value: 'released', label: 'Released' },
		{ value: 'unreleased', label: 'Unreleased' }
	];

	// A mockup: what will come from another source is written as the name of its field.
	const MOCK = {
		collective: 'Collective',
		country: 'Country',
		scenes: 'Scenes'
	};

	const labels = $derived(album.credits.find((group) => group.role === 'Label')?.artists ?? []);
	const tooltip = $derived(
		[album.base_name, album.variant, album.disambiguator].filter(Boolean).join(' ')
	);
	let adding = $state(false);
	const date = $derived(formatFullDate(album.release_date, album.release_date_precision));
</script>

{#snippet editTitle()}
	<TitleFields bind:draft placeholder="subtitle, for example Deluxe Version" />
{/snippet}

<!-- Two blocks, for the two rows of the grid of the page: the title with the facts of the release, and the facts about it. -->
<header
	class="space-y-5 rounded-t-xl bg-card px-4 pt-4 min-[1200px]:col-start-1 min-[1200px]:row-start-1"
>
	<EntityTitle
		title={album.base_name}
		{tooltip}
		genius={album.genius_url}
		edit={draft ? editTitle : undefined}
	>
		{#snippet after()}
			{#if album.variant}<span class="font-normal text-subtle">{album.variant}</span>{/if}
			{#if album.disambiguator}
				<span class="text-base font-normal text-subtle">{album.disambiguator}</span>
			{/if}
		{/snippet}
		{#if draft}
			<!-- The artists of the draft; the plus opens the search of an artist to add (the cross takes one off). -->
			<span class="inline-flex flex-wrap items-center gap-1.5 align-middle">
				{#each draft.artists as artist (artist.id)}
					<span class="inline-flex items-center gap-0.5 rounded-md bg-muted px-1.5 py-0.5 text-sm">
						{artist.base_name}
						<button
							type="button"
							class="text-subtle hover:text-destructive"
							aria-label="Take {artist.base_name} off the album"
							onclick={() => draft && (draft.artists = draft.artists.filter((a) => a !== artist))}
						>
							<X class="size-3.5" />
						</button>
					</span>
				{/each}
				<Button
					size="icon"
					aria-label="Add an artist"
					aria-pressed={adding}
					onclick={() => (adding = !adding)}
				>
					<Plus />
				</Button>
			</span>
		{:else}
			<ArtistLinks artists={album.artists} tinted />
		{/if}
	</EntityTitle>
	{#if draft && adding}
		<ArtistPick
			label="Add an artist to the album"
			onpick={(artist) => {
				if (draft && !draft.artists.some((a) => a.id === artist.id)) {
					draft.artists = [...draft.artists, { id: artist.id, base_name: artist.base_name }];
				}
				adding = false;
			}}
		/>
	{/if}

	<!-- Two groups: the facts of the release itself and the facts about it. The first one always has its four rows
	     (an unknown label is a dash), so the second one starts at the same place on every album. -->
	<dl>
		{#if draft}
			<!-- The rows keep their height: the type and the status are compact choices in the row of the type (a
			     popup opens under them), and the date opens a small window. -->
			<FactRow label="Type">
				<span class="inline-flex flex-wrap items-center gap-x-3">
					<SelectField
						bind:value={draft.albumType}
						options={TYPES}
						label="Type"
						edited={draft.edited('album_type')}
						bind:reset={draft.reset.type}
						class="-mx-1.5 -my-px h-auto w-auto gap-1 border-transparent px-1.5 py-0 text-[length:inherit] leading-[inherit] data-[size=default]:h-auto"
					/>
					<SelectField
						bind:value={draft.status}
						options={STATUSES}
						label="Status"
						edited={draft.edited('is_released')}
						bind:reset={draft.reset.status}
						class="-mx-1.5 -my-px h-auto w-auto gap-1 border-transparent px-1.5 py-0 text-[length:inherit] leading-[inherit] data-[size=default]:h-auto"
					/>
				</span>
			</FactRow>
			<FactRow label="Released">
				<DateField
					bind:value={draft.releaseDate}
					label="Release date"
					edited={draft.edited('release_date')}
					bind:reset={draft.reset.date}
				/>
			</FactRow>
		{:else}
			<FactRow label="Type">
				{#if album.album_type}{typeName(album.album_type)}{:else}<span class="text-subtle">—</span
					>{/if}
				{#if album.is_released === false}<Badge variant="warning">Unreleased</Badge>{/if}
				{#if album.import_state === 'stub'}<Badge variant="warning"
						>Stub: not imported in full</Badge
					>{/if}
			</FactRow>
			<FactRow label="Released">{date ?? 'No date'}</FactRow>
		{/if}
		<FactRow label="Label">
			{#if labels.length}
				<ClampList items={labels} lines={1} float>
					{#snippet item({ artist })}<a href={resolve('/artists/[id]', { id: String(artist.id) })}
							>{artist.base_name}</a
						>{/snippet}
				</ClampList>
			{:else}<span class="text-subtle">—</span>{/if}
		</FactRow>
		<FactRow label="Collective">{MOCK.collective}</FactRow>
	</dl>
</header>

<!-- The facts about the release, in two parts for two rows of the grid of the page: the tiles of the descriptors
     stand beside the second one, whatever the first one holds. The title and the groups share one grey panel: the
     gap before this group is padding, not margin, so the grey has no seam. -->
<dl class="bg-card px-4 min-[1200px]:col-start-1 min-[1200px]:row-start-2">
	<FactRow label="Country">{MOCK.country}</FactRow>
	{#if album.language}<FactRow label="Language">{languageName(album.language)}</FactRow>{/if}
</dl>
<dl class="rounded-b-xl bg-card px-4 min-[1200px]:col-start-1 min-[1200px]:row-start-3">
	<FactRow label="Scenes">{MOCK.scenes}</FactRow>
	<FactRow label="Genres">
		<!-- The genres of the songs of the album, the most common first, and under them smaller the tags of the songs. -->
		{#if album.genres.length}<CommaList items={album.genres} />{:else}<span class="text-subtle"
				>—</span
			>{/if}
		{#if album.tags.length}
			<div class="text-xs leading-snug text-muted-foreground">
				<CommaList items={album.tags} />
			</div>
		{/if}
	</FactRow>
</dl>
