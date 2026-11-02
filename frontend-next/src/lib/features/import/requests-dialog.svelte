<script lang="ts">
	import type { Job } from '#lib/api/client.js';
	import * as Dialog from '#lib/components/ui/dialog/index.js';
	import { Input } from '#lib/components/ui/input/index.js';
	import { Toggle } from '#lib/components/ui/toggle/index.js';
	import { RequestFeed } from '#lib/features/import/imports.svelte.js';
	import { endpointOf, isProblem, taskName } from '#lib/features/import/imports.js';
	import RequestTable from '#lib/features/import/request-table.svelte';
	import { poll } from '#lib/utils/poll.js';

	type Props = { job: Job | null; active: boolean; onclose: () => void };

	let { job, active, onclose }: Props = $props();

	const SHOWN = 1500; // more rows than this make the page heavy and nobody reads them one by one

	let query = $state('');
	let problemsOnly = $state(false);
	let feed = $state<RequestFeed | null>(null);

	$effect(() => {
		if (!job) {
			feed = null;
			return;
		}
		const current = new RequestFeed(job.id);
		feed = current;
		if (!active) {
			void current.refresh();
			return;
		}
		// Live while the job runs: the newest rows come every second.
		return poll(
			() => current.refresh(),
			() => 1000
		);
	});

	const problems = $derived((feed?.rows ?? []).filter(isProblem).length);

	const visible = $derived.by(() => {
		const text = query.trim().toLowerCase();
		const rows = (feed?.rows ?? []).filter((row) => {
			if (problemsOnly && !isProblem(row)) return false;
			if (!text) return true;
			const haystack = `${taskName(row.task_name, row.task_genius_id)} ${endpointOf(row.url)} ${row.status_code ?? 'network'}`;
			return haystack.toLowerCase().includes(text);
		});
		return rows.slice(-SHOWN).reverse(); // newest first
	});
</script>

<!-- The owner closes the dialog (job = null), so `open` only mirrors that. -->
<Dialog.Root open={job !== null} onOpenChange={onclose}>
	<Dialog.Content class="flex h-[85dvh] flex-col gap-0 p-0 sm:max-w-5xl">
		<Dialog.Header class="flex-row flex-wrap items-center gap-3 p-4 pr-14">
			<div class="mr-auto min-w-0">
				<Dialog.Title class="truncate">
					Requests · {job?.subject_name ?? `#${job?.genius_id}`}
				</Dialog.Title>
				<Dialog.Description class="tabular-nums">
					{feed?.rows.length ?? 0} requests{active ? ', updating live' : ''}
				</Dialog.Description>
			</div>
			<Toggle bind:pressed={problemsOnly} title="Errors, retries and answers that took 3 s or more">
				Errors {problems}
			</Toggle>
			<Input
				class="w-56"
				bind:value={query}
				placeholder="Filter: task, path, status"
				aria-label="Filter"
			/>
		</Dialog.Header>

		<div class="min-h-0 flex-1 overflow-auto">
			<RequestTable
				rows={visible}
				subjectId={job?.genius_id}
				empty={problemsOnly || query ? 'Nothing matches' : 'No requests yet'}
			/>
			{#if (feed?.rows.length ?? 0) > SHOWN}
				<p class="p-3 text-center text-xs text-subtle">
					Showing the newest {SHOWN}; use the filter to find older ones
				</p>
			{/if}
		</div>
	</Dialog.Content>
</Dialog.Root>
