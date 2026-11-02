<script lang="ts">
	import type { Job } from '#lib/api/client.js';
	import JobCard from '#lib/features/import/job-card.svelte';
	import Monitor from '#lib/features/import/monitor.svelte';
	import NewImport from '#lib/features/import/new-import.svelte';
	import Nesting from '#lib/features/import/nesting.svelte';
	import RequestsDialog from '#lib/features/import/requests-dialog.svelte';
	import { ImportJobs } from '#lib/features/import/imports.svelte.js';
	import { isActive } from '#lib/features/import/imports.js';
	import { poll } from '#lib/utils/poll.js';

	const imports = new ImportJobs();

	let now = $state(Date.now());
	let logJob = $state<Job | null>(null);
	// The one that runs now (jobs go one at a time); the list is newest first.
	const running = $derived(imports.jobs.find((j) => j.status === 'running') ?? null);
	// The dialog follows the live copy of the job, so it knows when the job has finished.
	const logActive = $derived(imports.jobs.some((j) => j.id === logJob?.id && isActive(j)));

	// A second while something runs (counters, clock), five seconds otherwise.
	$effect(() =>
		poll(
			async () => {
				await imports.refresh();
				now = Date.now();
			},
			() => (imports.active ? 1000 : 5000)
		)
	);
</script>

<!-- The monitor and under it the nesting of the walk are a column of their own, beside the form and the jobs, and stay
     in view while the jobs scroll. -->
<div class="grid items-start gap-6 lg:grid-cols-[minmax(0,1fr)_26.25rem]">
	<div class="space-y-6">
		<NewImport onstart={(body) => imports.start(body)} />

		<section class="space-y-4">
			{#if imports.offline}<p class="text-sm text-destructive">The backend does not answer</p>{/if}

			{#each imports.jobs as job (job.id)}
				<JobCard {job} oncancel={(j) => imports.cancel(j)} onlog={(j) => (logJob = j)} />
			{:else}
				<p class="rounded-xl bg-card p-10 text-center text-sm text-subtle">No imports yet</p>
			{/each}
		</section>
	</div>

	<div class="space-y-6 lg:sticky lg:top-16">
		<Monitor job={running} {now} monitor={imports.monitor} />
		<Nesting job={running ?? imports.jobs[0] ?? null} />
	</div>
</div>

<RequestsDialog job={logJob} active={logActive} onclose={() => (logJob = null)} />
