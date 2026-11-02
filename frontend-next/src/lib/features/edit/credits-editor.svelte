<script lang="ts">
	import X from '@lucide/svelte/icons/x';
	import { api } from '#lib/api/client.js';
	import { Button } from '#lib/components/ui/button/index.js';
	import { Input } from '#lib/components/ui/input/index.js';
	import ArtistPick from '#lib/features/edit/artist-pick.svelte';
	import { sortRoleNames } from '#lib/utils/albums.js';

	// The credits of an album or a song as a list of (role, artist) to take out of and to add to. A role is typed (the
	// roles that exist are suggested), and an artist is picked by search; a role that is new is made when the page is saved.
	export type DraftCredit = { role: string; artist: { id: number; base_name: string } };

	let { credits = $bindable() }: { credits: DraftCredit[] } = $props();

	const listId = $props.id();
	let role = $state('');
	let roles = $state<string[]>([]);
	void api.GET('/api/v1/credit-roles').then(({ data }) => (roles = data?.map((r) => r.name) ?? []));

	// The order of the page: producers and writers first.
	const ordered = $derived(sortRoleNames([...new Set(credits.map((c) => c.role))]));

	function add(artist: { id: number; base_name: string }) {
		const name = role.trim();
		if (!name || credits.some((c) => c.role === name && c.artist.id === artist.id)) return;
		credits = [...credits, { role: name, artist: { id: artist.id, base_name: artist.base_name } }];
	}
</script>

<div class="space-y-3 rounded-xl bg-card p-4">
	<ul class="space-y-0.5" aria-label="Credits">
		{#each ordered as name (name)}
			{#each credits.filter((c) => c.role === name) as credit (credit.artist.id)}
				<li class="flex items-center gap-3 py-0.5 text-sm">
					<span class="w-32 shrink-0 truncate text-[13px] text-subtle">{credit.role}</span>
					<span class="min-w-0 flex-1 truncate text-body">{credit.artist.base_name}</span>
					<Button
						variant="close"
						size="icon"
						aria-label="Take {credit.artist.base_name} out of {credit.role}"
						onclick={() => (credits = credits.filter((c) => c !== credit))}
					>
						<X />
					</Button>
				</li>
			{/each}
		{:else}
			<li class="py-2 text-center text-sm text-muted-foreground">No credits</li>
		{/each}
	</ul>
	<div class="flex items-start gap-2">
		<Input
			bind:value={role}
			list={listId}
			aria-label="Role of the credit"
			placeholder="role"
			class="w-36 shrink-0 border-transparent"
		/>
		<datalist id={listId}>
			{#each roles as name (name)}<option value={name}></option>{/each}
		</datalist>
		<div class="min-w-0 flex-1">
			<ArtistPick label="Add an artist to the role" onpick={add} />
		</div>
	</div>
</div>
