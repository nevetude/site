<script lang="ts">
	import type { ArtistDetail } from '#lib/api/client.js';
	import EntityTitle from '#lib/components/entity-title.svelte';
	import FactRow from '#lib/components/fact-row.svelte';
	import { formatCount, formatFullDate } from '#lib/utils/format.js';
	import { Badge } from '#lib/components/ui/badge/index.js';
	import ClampList from '#lib/components/clamp-list.svelte';
	import type { ArtistDraft } from '#lib/features/artist/artist-draft.svelte.js';
	import { Input } from '#lib/components/ui/input/index.js';
	import ResetField from '#lib/features/edit/reset-field.svelte';
	import SelectField from '#lib/features/edit/select-field.svelte';
	import { nameTimeline } from '#lib/utils/nicknames.js';

	// `draft`: the page is being edited, and the type and the names are fields.
	let { artist, draft = $bindable(null) }: { artist: ArtistDetail; draft?: ArtistDraft | null } =
		$props();

	const TYPES = [
		{ value: '', label: '—' },
		...['person', 'group', 'label', 'other'].map((value) => ({
			value,
			label: value[0].toUpperCase() + value.slice(1)
		}))
	];
	const timeline = $derived(nameTimeline(artist.nicknames));
	const egos = $derived(artist.nicknames.filter((n) => n.kind === 'alter_ego').map((n) => n.name));

	const typeName = (type: string) => type[0].toUpperCase() + type.slice(1);
	const works = $derived(
		[
			artist.albums_count &&
				`${artist.albums_count} ${artist.albums_count === 1 ? 'album' : 'albums'}`,
			artist.songs_count && `${artist.songs_count} ${artist.songs_count === 1 ? 'song' : 'songs'}`
		].filter(Boolean)
	);
	// Only the facts that are known: Genius has no place of birth or death as a field, so there is no row for them.
	const person = $derived(
		[
			{
				label: 'Born',
				value: artist.born && formatFullDate(artist.born.date, artist.born.precision)
			},
			{
				label: 'Died',
				value: artist.died && formatFullDate(artist.died.date, artist.died.precision)
			}
		].filter((row) => row.value)
	);
</script>

{#snippet editTitle()}
	<!-- The name stays as it is (its names are edited beside); what tells two artists of one name apart is a field on the same line. -->
	<div class="flex items-center gap-2">
		<h1 class="max-w-[50%] shrink-0 truncate text-[1.2rem] leading-tight font-bold">
			{artist.base_name}
		</h1>
		<ResetField
			edited={draft!.edited('disambiguator')}
			bind:reset={draft!.reset.disambiguator}
			label="disambiguator"
		>
			<Input
				bind:value={draft!.disambiguator}
				aria-label="Disambiguator"
				placeholder="disambiguator"
				disabled={draft!.reset.disambiguator}
				class="h-8 border-transparent"
			/>
		</ResetField>
	</div>
	<ResetField
		edited={draft!.edited('real_name')}
		bind:reset={draft!.reset.realName}
		label="real name"
	>
		<Input
			bind:value={draft!.realName}
			aria-label="Real name"
			placeholder="real name"
			disabled={draft!.reset.realName}
			class="border-transparent text-[14px] md:text-[14px]"
		/>
	</ResetField>
{/snippet}

<header class="space-y-5">
	<!-- What tells two artists of one name apart stands after the name; the line under it is the real name. -->
	<EntityTitle
		title={artist.base_name}
		genius={artist.genius_url}
		edit={draft ? editTitle : undefined}
	>
		{#snippet after()}
			{#if artist.disambiguator}<span class="text-base font-normal text-subtle"
					>{artist.disambiguator}</span
				>{/if}
		{/snippet}
		{#if !draft && artist.real_name}<span class="text-[14px] font-normal text-muted-foreground"
				>{artist.real_name}</span
			>{/if}
	</EntityTitle>

	<dl>
		<FactRow label="Type">
			{#if draft}
				<SelectField
					bind:value={draft.artistType}
					options={TYPES}
					label="Type"
					edited={draft.edited('artist_type')}
					bind:reset={draft.reset.type}
				/>
			{:else}
				{#if artist.artist_type}{typeName(artist.artist_type)}{:else}<span class="text-subtle"
						>—</span
					>{/if}
				{#if artist.import_state === 'stub'}<Badge variant="warning"
						>Stub: not imported in full</Badge
					>{/if}
				{#if artist.is_meme_verified}<Badge>Meme verified</Badge>{/if}
			{/if}
		</FactRow>
		<FactRow label="Followers">
			{#if artist.followers_count}{formatCount(artist.followers_count)}{:else}<span
					class="text-subtle">—</span
				>{/if}
		</FactRow>
		{#if works.length}<FactRow label="Works">{works.join(' · ')}</FactRow>{/if}
		{#if !draft && timeline.length > 1}
			<FactRow label="Names">
				{#each timeline as step, i (i)}
					{#if i}<span class="mx-1 text-subtle">→</span>{/if}{step.name}{#if step.from}<span
							class="ml-1 text-subtle tabular-nums">({step.from})</span
						>{/if}
				{/each}
			</FactRow>
		{/if}
		{#if !draft && egos.length}<FactRow label="Alter egos">{egos.join(', ')}</FactRow>{/if}
		{#if !draft && artist.aliases.length}
			<FactRow label="Also known as">
				<ClampList items={artist.aliases} lines={1} float>
					{#snippet item(alias)}{alias}{/snippet}
				</ClampList>
			</FactRow>
		{/if}
	</dl>
	{#if person.length}
		<dl>
			{#each person as row (row.label)}<FactRow label={row.label}>{row.value}</FactRow>{/each}
		</dl>
	{/if}
</header>
