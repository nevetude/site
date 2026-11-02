<script lang="ts">
	import ChevronRight from '@lucide/svelte/icons/chevron-right';
	import Clock from '@lucide/svelte/icons/clock';
	import Gauge from '@lucide/svelte/icons/gauge';
	import Hourglass from '@lucide/svelte/icons/hourglass';
	import Send from '@lucide/svelte/icons/send';
	import type { Snippet } from 'svelte';
	import type { Job, Monitor } from '#lib/api/client.js';
	import { Badge } from '#lib/components/ui/badge/index.js';
	import * as Card from '#lib/components/ui/card/index.js';
	import {
		KINDS,
		elapsedMs,
		etaMs,
		formatBytes,
		formatDuration,
		formatMs,
		tookTone
	} from '#lib/features/import/imports.js';

	type Props = { job: Job | null; now: number; monitor: Monitor | null };

	let { job, now, monitor }: Props = $props();

	// The four numbers are always there; the server, the response time and the answers open under them.
	let more = $state(false);

	const elapsed = $derived(job ? elapsedMs(job, now) : null);
	const eta = $derived(job ? etaMs(job, now) : null);
	const perMinute = $derived(
		job && elapsed && elapsed > 5000 ? Math.round((job.requests_total / elapsed) * 60_000) : null
	);

	const stats = $derived([
		{ label: 'Elapsed', icon: Clock, value: elapsed === null ? '—' : formatDuration(elapsed) },
		{
			label: 'Time left',
			icon: Hourglass,
			value: !job ? '—' : eta === null ? 'estimating…' : formatDuration(eta)
		},
		{ label: 'Requests', icon: Send, value: job ? String(job.requests_total) : '—' },
		{ label: 'Per minute', icon: Gauge, value: perMinute === null ? '—' : String(perMinute) }
	]);

	const connection = $derived(monitor?.connection);
	const latency = $derived(monitor?.latency);
	const answers = $derived(monitor?.answers);

	const server = $derived<[string, string | null | undefined][]>([
		['Host', connection?.host],
		['Address', connection?.ip],
		['Edge', connection && [connection.server, connection.edge].filter(Boolean).join(' · ')],
		['Origin', connection?.origin],
		[
			'Protocol',
			connection && [connection.http_version, connection.tls_version].filter(Boolean).join(' · ')
		]
	]);

	const latencies = $derived<[string, number | undefined][]>([
		['Last', latency?.last_ms],
		['Median', latency?.median_ms],
		['95th', latency?.p95_ms],
		['Worst', latency?.worst_ms]
	]);

	// Answers worth a look are marked, the plain zeros are not.
	const results = $derived<[string, number | undefined, 'warning' | 'destructive' | null][]>([
		['OK', answers?.ok, null],
		['Not found', answers?.client_errors, 'warning'],
		['Rate limited', answers?.rate_limited, 'destructive'],
		['Server errors', answers?.server_errors, 'destructive'],
		['No answer', answers?.no_answer, 'destructive'],
		['Retries', answers?.retries, 'warning']
	]);

	const TONE = {
		success: 'text-success',
		warning: 'text-warning',
		destructive: 'text-destructive'
	};
	const BAR = {
		success: 'bg-success/50',
		warning: 'bg-warning/60',
		destructive: 'bg-destructive/60'
	};
	// The bars are as tall as the slowest answer of the chart, so one slow answer does not flatten the rest.
	const chartMax = $derived(Math.max(1, ...(latency?.recent_ms ?? [])));
</script>

{#snippet section(title: string, note: string | undefined, body: Snippet)}
	<section class="space-y-2 pt-4">
		<h3 class="flex items-baseline justify-between text-xs font-medium text-muted-foreground">
			{title}{#if note}<span class="font-normal text-subtle">{note}</span>{/if}
		</h3>
		{@render body()}
	</section>
{/snippet}

{#snippet row(label: string, value: string | null | undefined)}
	<div class="flex items-baseline justify-between gap-3 text-sm">
		<dt class="text-xs text-muted-foreground">{label}</dt>
		<dd class="truncate text-right tabular-nums" title={value || undefined}>
			{value || '—'}
		</dd>
	</div>
{/snippet}

{#snippet serverBody()}
	<dl class="space-y-1.5">
		{#each server as [label, value] (label)}{@render row(label, value)}{/each}
	</dl>
{/snippet}

{#snippet latencyBody()}
	<dl class="grid grid-cols-4 gap-2">
		{#each latencies as [label, ms] (label)}
			<div class="min-w-0">
				<dt class="text-xs text-muted-foreground">{label}</dt>
				<dd
					class="truncate text-sm font-semibold tabular-nums {ms === undefined
						? 'text-subtle'
						: TONE[tookTone(ms)]}"
				>
					{ms === undefined ? '—' : formatMs(ms)}
				</dd>
			</div>
		{/each}
	</dl>
	<div class="flex h-10 items-end gap-px" aria-hidden="true">
		{#each latency?.recent_ms ?? [] as ms, i (i)}
			<span
				class="min-w-px flex-1 rounded-t-[1px] {BAR[tookTone(ms)]}"
				style:height="{Math.max(6, (ms / chartMax) * 100)}%"
				title={formatMs(ms)}
			></span>
		{:else}
			<span class="h-px w-full self-center bg-border"></span>
		{/each}
	</div>
{/snippet}

{#snippet answersBody()}
	<dl class="grid grid-cols-3 gap-x-3 gap-y-2">
		{#each results as [label, count, tone] (label)}
			<div class="min-w-0">
				<dt class="truncate text-xs text-muted-foreground">{label}</dt>
				<dd
					class="text-sm font-semibold tabular-nums {!count
						? 'text-subtle'
						: tone
							? TONE[tone]
							: ''}"
				>
					{count ?? '—'}
				</dd>
			</div>
		{/each}
	</dl>
	<dl class="space-y-1.5">
		{@render row('Downloaded', answers?.requests ? formatBytes(answers.bytes) : null)}
		{@render row(
			'Pace',
			monitor
				? `at most one request per ${formatMs(Math.round(monitor.min_interval_s * 1000))}`
				: null
		)}
	</dl>
{/snippet}

<Card.Root class="[--card-spacing:--spacing(5)]">
	<Card.Header>
		<Card.Title>Monitor</Card.Title>
		<Card.Description class="truncate">
			{job
				? `${KINDS[job.kind].one} · ${job.subject_name ?? `#${job.genius_id}`}`
				: 'Nothing is running'}
		</Card.Description>
		<Card.Action
			><Badge variant={job ? 'success' : 'default'}>{job ? 'Running' : 'Idle'}</Badge></Card.Action
		>
	</Card.Header>

	<Card.Content class="space-y-4">
		<dl class="grid grid-cols-2 gap-2">
			{#each stats as stat (stat.label)}
				<div class="rounded-lg bg-muted/60 p-3">
					<dt class="flex items-center gap-1.5 text-xs text-muted-foreground">
						<stat.icon class="size-3.5" aria-hidden="true" />
						{stat.label}
					</dt>
					<dd class="mt-1 truncate text-lg font-semibold tabular-nums {job ? '' : 'text-subtle'}">
						{stat.value}
					</dd>
				</div>
			{/each}
		</dl>

		<button
			type="button"
			aria-expanded={more}
			class="flex w-full items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground"
			onclick={() => (more = !more)}
		>
			<ChevronRight class="size-3.5 transition-transform {more ? 'rotate-90' : ''}" />
			{more ? 'Less' : 'More'}
		</button>
		{#if more}
			<div class="space-y-4">
				{@render section('Server', undefined, serverBody)}
				{@render section(
					'Response time',
					latency ? `last ${latency.samples} requests` : undefined,
					latencyBody
				)}
				{@render section(
					'Answers',
					answers?.requests ? `last ${answers.requests} requests` : undefined,
					answersBody
				)}
			</div>
		{/if}
	</Card.Content>
</Card.Root>
