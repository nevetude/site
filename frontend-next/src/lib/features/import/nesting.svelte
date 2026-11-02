<script lang="ts">
	import Repeat from '@lucide/svelte/icons/repeat-2';
	import { api, type Job, type NestingNode } from '#lib/api/client.js';
	import * as Card from '#lib/components/ui/card/index.js';
	import { isActive, nestingRows } from '#lib/features/import/imports.js';
	import { poll } from '#lib/utils/poll.js';

	// The artists the job meets on its walk over groups and members, live: each one under the artist that found it,
	// and what was found again (a person in a second group, a loop back to a group already met) marked with the
	// groups that found it again. There is no depth limit on the walk, so this is how to see how far it has gone.
	type Props = { job: Job | null };

	let { job }: Props = $props();

	let nodes = $state<NestingNode[]>([]);
	const rows = $derived(nestingRows(nodes));
	const names = $derived(new Map(nodes.map((n) => [n.genius_id, n.name ?? `#${n.genius_id}`])));

	$effect(() => {
		const id = job?.id;
		if (id === undefined) {
			nodes = [];
			return;
		}
		return poll(
			async () => {
				const { data } = await api.GET('/api/v1/imports/{job_id}/nesting', {
					params: { path: { job_id: id } }
				});
				if (data) nodes = data;
			},
			() => (job && isActive(job) ? 1000 : 60_000)
		);
	});

	const DOT = {
		queued: 'bg-subtle',
		running: 'bg-warning animate-pulse',
		done: 'bg-success',
		failed: 'bg-destructive'
	};
</script>

<Card.Root class="[--card-spacing:--spacing(5)]">
	<Card.Header>
		<Card.Title>Nesting</Card.Title>
		<Card.Description>
			{rows.length ? `${rows.length} artists in groups` : 'Nothing nested yet'}
		</Card.Description>
	</Card.Header>

	{#if rows.length}
		<Card.Content>
			<ul class="max-h-80 space-y-0.5 overflow-auto text-sm" aria-label="Nesting of the import">
				{#each rows as { node, depth } (node.genius_id)}
					<li
						class="flex min-w-0 items-center gap-2 py-0.5"
						style:padding-left="{depth * 14}px"
						data-state={node.state}
					>
						<span class="size-1.5 shrink-0 rounded-full {DOT[node.state]}" aria-hidden="true"
						></span>
						<span class="min-w-0 truncate">{node.name ?? `#${node.genius_id}`}</span>
						{#if node.kind}
							<span class="shrink-0 text-xs text-subtle"
								>{node.kind === 'person' ? 'artist' : node.kind}</span
							>
						{/if}
						{#if node.also_in.length}
							<span
								class="flex min-w-0 shrink items-center gap-1 text-xs text-muted-foreground"
								title="Found again by {node.also_in.map((id) => names.get(id)).join(', ')}"
							>
								<Repeat class="size-3 shrink-0" aria-hidden="true" />
								<span class="truncate">{node.also_in.map((id) => names.get(id)).join(', ')}</span>
							</span>
						{/if}
					</li>
				{/each}
			</ul>
		</Card.Content>
	{/if}
</Card.Root>
