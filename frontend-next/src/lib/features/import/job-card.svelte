<script lang="ts">
	import List from '@lucide/svelte/icons/list';
	import type { Job } from '#lib/api/client.js';
	import { Badge } from '#lib/components/ui/badge/index.js';
	import { Button } from '#lib/components/ui/button/index.js';
	import * as Card from '#lib/components/ui/card/index.js';
	import { Progress } from '#lib/components/ui/progress/index.js';
	import RequestTable from '#lib/features/import/request-table.svelte';
	import Stat from '#lib/features/import/stat.svelte';
	import {
		KINDS,
		elapsedMs,
		formatDuration,
		isActive,
		statusTone,
		sum,
		taskLabel
	} from '#lib/features/import/imports.js';

	type Props = {
		job: Job;
		oncancel: (job: Job) => void;
		onlog: (job: Job) => void;
	};

	let { job, oncancel, onlog }: Props = $props();

	const STATUS_TEXT = {
		queued: 'Queued',
		running: 'Running',
		succeeded: 'Done',
		failed: 'Failed',
		cancelled: 'Cancelled'
	};

	// A running job always shows its latest requests; a finished one only when asked, to keep the history short.
	let showRecent = $state(false);
	const active = $derived(isActive(job));
	const progress = $derived(job.progress);
	const units = $derived(progress ? sum(progress.units) : null);
	const items = $derived(progress ? sum(progress.items) : null);
	const failures = $derived(job.error ? job.error.split('; ') : []);
	const finishedWithErrors = $derived(job.status === 'succeeded' && failures.length > 0);
	const statusText = $derived(finishedWithErrors ? 'Done with errors' : STATUS_TEXT[job.status]);
	const current = $derived(progress?.unit);
</script>

<Card.Root class="[--card-spacing:--spacing(5)]">
	<Card.Header>
		<Card.Description class="tracking-wider uppercase">{KINDS[job.kind].one}</Card.Description>
		<Card.Title class="truncate text-lg">
			{job.subject_name ?? progress?.root?.name ?? `Genius #${job.genius_id}`}
		</Card.Title>
		<Card.Action class="flex items-center gap-2">
			<Badge variant={finishedWithErrors ? 'warning' : statusTone[job.status]}>{statusText}</Badge>
			{#if active}
				<Button variant="destructive" onclick={() => oncancel(job)}>Cancel</Button>
			{/if}
		</Card.Action>
	</Card.Header>

	<Card.Content class="space-y-4">
		{#if active}
			{#if units && progress}
				<div class="grid grid-cols-[repeat(auto-fit,minmax(6.125rem,1fr))] gap-4">
					{#each progress.units as count (count.kind)}
						<Stat label={KINDS[count.kind].many} done={count.done} total={count.total} />
					{/each}
				</div>
				<Progress value={units.done} max={units.total} aria-label="All steps of the import" />

				{#if current}
					<div class="space-y-3 rounded-lg bg-muted/60 p-4">
						<div class="flex items-baseline justify-between gap-3">
							<div class="min-w-0">
								<div class="text-xs tracking-wider text-muted-foreground uppercase">
									Now: {KINDS[current.kind].one.toLowerCase()}
								</div>
								<div class="truncate font-medium">{current.name ?? `#${current.genius_id}`}</div>
							</div>
							<div class="flex shrink-0 gap-5">
								{#each progress.items as count (count.kind)}
									<Stat label={KINDS[count.kind].many} done={count.done} total={count.total} />
								{/each}
							</div>
						</div>
						<Progress
							value={items?.done ?? 0}
							max={items?.total || 1}
							class="h-1"
							aria-label="Contents of the current item"
						/>
					</div>
				{/if}
			{:else}
				<p class="text-sm text-muted-foreground">
					{job.status === 'queued' ? 'Waiting for the previous import…' : 'Reading the list…'}
				</p>
			{/if}

			{#if progress?.active}
				<p class="truncate text-xs text-muted-foreground">
					{taskLabel(progress.active.kind, progress.active.genius_id, progress.active.name)}
				</p>
			{/if}
		{:else}
			<p class="text-sm text-muted-foreground">
				{job.message ?? statusText}
				{#if job.started_at && job.finished_at}
					<span class="ml-1 text-subtle tabular-nums">· {formatDuration(elapsedMs(job, 0))}</span>
				{/if}
			</p>
			{#if failures.length}
				<ul class="space-y-1 text-xs text-destructive">
					{#each failures as failure (failure)}<li class="break-words">{failure}</li>{/each}
				</ul>
			{/if}
		{/if}
	</Card.Content>

	{#if job.requests_total > 0}
		<Card.Footer class="flex-col items-stretch gap-2">
			<div class="flex items-center justify-between">
				<Button variant="ghost" disabled={active} onclick={() => (showRecent = !showRecent)}>
					Last {job.recent_requests.length} of {job.requests_total} requests
				</Button>
				<Button variant="ghost" onclick={() => onlog(job)}>
					<List /> All requests
				</Button>
			</div>
			{#if active || showRecent}
				<RequestTable rows={[...job.recent_requests].reverse()} subjectId={job.genius_id} />
			{/if}
		</Card.Footer>
	{/if}
</Card.Root>
