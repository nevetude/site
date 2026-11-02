<script lang="ts">
	import X from '@lucide/svelte/icons/x';
	import type { PreviewMember } from '#lib/api/client.js';
	import ArtistSearch from '#lib/features/import/artist-search.svelte';
	import { Button } from '#lib/components/ui/button/index.js';
	import { Checkbox } from '#lib/components/ui/checkbox/index.js';
	import Thumb from '#lib/components/thumb.svelte';

	// The people an import of a group brings with it, before it starts: the ones Genius lists (or the saved list of
	// the group), each with a cross to take it out, and a search to add more. Whoever is added is imported with the
	// group though Genius does not list them in it. `discographies`: import every member with all their albums, not only
	// the artist. The list and the choice are saved to the file of the group when Import is pressed.
	type Props = { members: PreviewMember[]; discographies: boolean; saved: boolean };

	let { members = $bindable(), discographies = $bindable(), saved }: Props = $props();

	const remove = (id: number) => (members = members.filter((m) => m.genius_id !== id));
</script>

<div class="space-y-3 rounded-lg bg-muted/40 p-3">
	<ul class="space-y-0.5" aria-label="Members of the group">
		{#each members as member (member.genius_id)}
			<li class="flex items-center gap-3 rounded-md px-1 py-1">
				<Thumb src={member.image_url} name={member.name} class="size-7 rounded-md" />
				<span class="min-w-0 flex-1 truncate text-sm">{member.name}</span>
				{#if member.source === 'saved'}
					<span class="text-xs text-subtle" title="Genius does not list this person in the group"
						>added</span
					>
				{/if}
				<span class="text-xs text-subtle tabular-nums">{member.genius_id}</span>
				<Button
					variant="close"
					size="icon"
					aria-label="Take {member.name} out of the group"
					onclick={() => remove(member.genius_id)}
				>
					<X />
				</Button>
			</li>
		{:else}
			<li class="p-2 text-center text-sm text-muted-foreground">Nobody: add people below</li>
		{/each}
	</ul>
	<label class="flex w-fit items-center gap-2 text-sm text-muted-foreground">
		<Checkbox bind:checked={discographies} />
		Discographies of the members
	</label>
	{#if saved}<p class="text-xs text-subtle">The list is the saved one of this group.</p>{/if}
	<ArtistSearch
		label="Add a member"
		chosen={members.map((m) => m.genius_id)}
		onpick={(hit) => {
			if (members.some((m) => m.genius_id === hit.genius_id)) return;
			members = [
				...members,
				{
					genius_id: hit.genius_id,
					name: hit.name,
					image_url: hit.image_url,
					source: 'saved',
					has_left: false
				}
			];
		}}
	/>
</div>
