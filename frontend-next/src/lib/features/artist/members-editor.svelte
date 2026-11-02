<script lang="ts">
	import ChevronDown from '@lucide/svelte/icons/chevron-down';
	import ChevronUp from '@lucide/svelte/icons/chevron-up';
	import X from '@lucide/svelte/icons/x';
	import Thumb from '#lib/components/thumb.svelte';
	import { Button } from '#lib/components/ui/button/index.js';
	import { Checkbox } from '#lib/components/ui/checkbox/index.js';
	import type { ArtistDraft } from '#lib/features/artist/artist-draft.svelte.js';
	import BoundaryField from '#lib/features/artist/boundary-field.svelte';
	import ArtistPick from '#lib/features/edit/artist-pick.svelte';
	import { moved } from '#lib/utils/list.js';

	// The members of a group, in the order they are shown, with the time each one was in it. A member that Genius lists
	// and is taken out here is only hidden: the import cannot bring them back. An artist is added from the library.
	let { draft = $bindable(), artistId }: { draft: ArtistDraft | null; artistId: number } = $props();
</script>

{#if draft}
	<section class="space-y-3 rounded-xl bg-card p-4" aria-label="Members">
		<h2 class="text-base font-semibold">Members</h2>
		<ul class="space-y-2" aria-label="Members of the group">
			{#each draft.members as member, i (member.id)}
				<li class="space-y-1.5 rounded-lg bg-muted/40 p-2">
					<div class="flex items-center gap-2">
						<Thumb src={member.cover} name={member.name} class="size-7 rounded-md" />
						<span class="min-w-0 flex-1 truncate text-sm">{member.name}</span>
						<Button
							variant="ghost"
							size="icon"
							aria-label="Move {member.name} up"
							disabled={i === 0}
							onclick={() => draft && (draft.members = moved(draft.members, i, i - 1))}
						>
							<ChevronUp />
						</Button>
						<Button
							variant="ghost"
							size="icon"
							aria-label="Move {member.name} down"
							disabled={i === (draft?.members.length ?? 0) - 1}
							onclick={() => draft && (draft.members = moved(draft.members, i, i + 1))}
						>
							<ChevronDown />
						</Button>
						<Button
							variant="close"
							size="icon"
							aria-label="Take {member.name} out of the group"
							onclick={() => draft && (draft.members = draft.members.filter((m) => m !== member))}
						>
							<X />
						</Button>
					</div>
					<div class="flex flex-wrap items-center gap-x-3 gap-y-1 pl-9 text-xs text-subtle">
						<span>from</span>
						<BoundaryField
							bind:boundary={draft.members[i].start}
							{artistId}
							label="Start of {member.name}"
						/>
						<span>to</span>
						<BoundaryField
							bind:boundary={draft.members[i].end}
							{artistId}
							label="End of {member.name}"
						/>
						<label class="flex items-center gap-1.5" title="Left the group, when is not known">
							<Checkbox
								bind:checked={draft.members[i].hasLeft}
								aria-label="{member.name} has left"
							/>
							left
						</label>
					</div>
				</li>
			{:else}
				<li class="py-2 text-center text-sm text-muted-foreground">
					Nobody yet: add an artist below
				</li>
			{/each}
		</ul>
		<ArtistPick
			label="Add a member"
			placeholder="add a member"
			onpick={(artist) => {
				if (!draft || draft.members.some((m) => m.id === artist.id)) return;
				draft.members = [
					...draft.members,
					{
						id: artist.id,
						name: artist.base_name,
						cover: artist.cover_url,
						start: { release: null, date: '' },
						end: { release: null, date: '' },
						hasLeft: false
					}
				];
			}}
		/>
	</section>
{/if}
