<script lang="ts">
	import { api, type Group, type ImportCreate, type PreviewMember } from '#lib/api/client.js';
	import { Button } from '#lib/components/ui/button/index.js';
	import * as Card from '#lib/components/ui/card/index.js';
	import { Input } from '#lib/components/ui/input/index.js';
	import * as Select from '#lib/components/ui/select/index.js';
	import { Spinner } from '#lib/components/ui/spinner/index.js';
	import ArtistSearch from '#lib/features/import/artist-search.svelte';
	import GroupMembers from '#lib/features/import/group-members.svelte';
	import { MODES, PREFIX, importBody, parseId, type Mode } from '#lib/features/import/imports.js';

	type Props = { onstart: (body: ImportCreate) => Promise<void> };

	let { onstart }: Props = $props();

	let mode = $state<Mode>('discography');
	let idText = $state('');
	let limitText = $state('');
	let starting = $state(false);

	// The group of the id that is typed: shown when the artist has members (or a saved list), so the people can be
	// settled before the import starts.
	let shown = $state(false);
	let members = $state<PreviewMember[]>([]);
	let groupName = $state('');
	let saved = $state(false);
	let discographies = $state(false);
	let savedGroups = $state<Group[]>([]);

	// Only artists are looked up by name; an album or a song is imported by the id from its page.
	const withSearch = $derived(mode === 'discography' || mode === 'artist');
	const group = $derived(
		shown
			? {
					name: groupName,
					members: members.map(({ genius_id, name, start, end, has_left }) => ({
						genius_id,
						name,
						start,
						end,
						has_left
					})),
					discographies
				}
			: null
	);
	const body = $derived(importBody(mode, idText, limitText, group));

	const loadSavedGroups = async () => {
		const { data } = await api.GET('/api/v1/groups');
		if (data) savedGroups = data;
	};
	void loadSavedGroups();

	$effect(() => {
		const id = withSearch ? parseId(idText) : null;
		if (id === null) {
			shown = false;
			return;
		}
		// A moment after the last key, so typing an id does not ask Genius for every prefix of it.
		const timer = setTimeout(async () => {
			const { data } = await api.GET('/api/v1/groups/{genius_id}', {
				params: { path: { genius_id: id } }
			});
			if (parseId(idText) !== id) return; // another id was typed meanwhile
			shown = !!data?.members.length;
			if (data) {
				members = data.members;
				groupName = data.name;
				saved = data.saved;
				discographies = data.discographies;
			}
		}, 400);
		return () => clearTimeout(timer);
	});

	async function start(event: SubmitEvent) {
		event.preventDefault();
		if (!body) return;
		starting = true;
		try {
			await onstart(body);
			await loadSavedGroups();
		} finally {
			starting = false;
		}
	}
</script>

<!-- No titles and no labels: the fields say what they are in a short grey hint (the label for a screen reader is
     `aria-label`), and no outlines, the fields are filled. -->
<Card.Root class="[--card-spacing:--spacing(5)]">
	<Card.Content class="space-y-4">
		{#if withSearch}
			<ArtistSearch
				label="Find an artist"
				chosen={[Number(idText)]}
				onpick={(hit) => (idText = String(hit.genius_id))}
			/>
			{#if savedGroups.length}
				<ul class="flex flex-wrap gap-1.5" aria-label="Saved groups">
					{#each savedGroups as one (one.genius_id)}
						<li>
							<Button
								class="text-muted-foreground"
								title="{one.members.length} members"
								onclick={() => (idText = String(one.genius_id))}
							>
								{one.name}
							</Button>
						</li>
					{/each}
				</ul>
			{/if}
			{#if shown}<GroupMembers bind:members bind:discographies {saved} />{/if}
		{/if}

		<form class="flex flex-wrap items-center gap-3" onsubmit={start}>
			<Select.Root bind:value={mode}>
				<Select.Trigger aria-label="Mode" class="w-64 border-transparent">
					{MODES.find((m) => m.value === mode)?.label}
				</Select.Trigger>
				<Select.Content>
					{#each MODES as m (m.value)}
						<Select.Item value={m.value} label={m.label} />
					{/each}
				</Select.Content>
			</Select.Root>

			{#if mode === 'discography'}
				<Input
					bind:value={idText}
					aria-label="Artist id"
					placeholder="id"
					class="w-28 border-transparent"
				/>
				<Input
					bind:value={limitText}
					aria-label="Albums limit"
					placeholder="limit"
					class="w-28 border-transparent"
				/>
			{:else}
				<span class="font-mono text-xs text-muted-foreground">{PREFIX[mode]}</span>
				<Input
					bind:value={idText}
					aria-label="Id"
					placeholder="id"
					class="w-40 border-transparent"
				/>
			{/if}

			<Button type="submit" class="ml-auto" disabled={!body || starting}>
				{#if starting}<Spinner />{/if}
				Import
			</Button>
		</form>
	</Card.Content>
</Card.Root>
