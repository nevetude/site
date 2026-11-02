<script lang="ts">
	import { resolve } from '$app/paths';
	import type { MemberOut } from '#lib/api/client.js';
	import Thumb from '#lib/components/thumb.svelte';
	import { Badge } from '#lib/components/ui/badge/index.js';
	import { formatPeriod } from '#lib/utils/format.js';

	// The members of a group, or the groups of a member, each with the time in the group when it is known.
	let { title, artists }: { title: string; artists: MemberOut[] } = $props();
</script>

{#if artists.length}
	<section class="space-y-3">
		<h2 class="flex items-baseline gap-3 text-base font-semibold text-foreground">
			{title}
			<span class="tabular-nums font-mono text-xs font-normal text-subtle">{artists.length}</span>
		</h2>
		<div class="grid grid-cols-[repeat(auto-fill,minmax(12.25rem,1fr))] gap-3">
			{#each artists as member (member.artist.id)}
				{@const period = formatPeriod(member)}
				<a
					href={resolve('/artists/[id]', { id: String(member.artist.id) })}
					class="flex items-center gap-3 rounded-xl bg-card p-2.5 hover:bg-muted/60"
				>
					<Thumb
						src={member.artist.cover_url}
						name={member.artist.base_name}
						class="size-10 rounded-lg"
					/>
					<span class="min-w-0 flex-1">
						<span class="block truncate text-sm text-foreground">{member.artist.base_name}</span>
						{#if period}
							<span class="block truncate text-xs text-subtle tabular-nums">{period}</span>
						{/if}
					</span>
					{#if member.artist.import_state === 'stub'}<Badge>Stub</Badge>{/if}
				</a>
			{/each}
		</div>
	</section>
{/if}
