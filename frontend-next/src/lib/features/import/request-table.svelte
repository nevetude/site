<script lang="ts">
	import ArrowDown from '@lucide/svelte/icons/arrow-down';
	import ArrowUp from '@lucide/svelte/icons/arrow-up';
	import type { RequestRow } from '#lib/api/client.js';
	import ExtLink from '#lib/components/ext-link.svelte';
	import { Badge } from '#lib/components/ui/badge/index.js';
	import { Button } from '#lib/components/ui/button/index.js';
	import * as Table from '#lib/components/ui/table/index.js';
	import {
		clockTime,
		endpointOf,
		formatBytes,
		nextSort,
		requestTone,
		sortRows,
		taskName,
		tookTone,
		type Sort,
		type SortKey
	} from '#lib/features/import/imports.js';

	type Props = {
		rows: RequestRow[];
		/** Genius id of the job's own artist or album: its row is an entry point too */
		subjectId?: number;
		empty?: string;
	};

	let { rows, subjectId, empty = 'No requests yet' }: Props = $props();

	const SORTABLE: { key: SortKey; heading: string }[] = [
		{ key: 'took', heading: 'Took' },
		{ key: 'size', heading: 'Size' }
	];
	// Text colour only, so a column of them stays quiet.
	const TOOK = {
		success: 'text-success/70',
		warning: 'text-warning',
		destructive: 'text-destructive'
	};

	let sort = $state<Sort>(null);
	const sorted = $derived(sortRows(rows, sort));

	// The big steps of an import are marked: the request of an album itself, and of the artist being imported.
	// Not the lists (an artist's albums, an album's tracks) nor the other artists.
	const OWN_PAGE = /^\/(artists|albums)\/\d+$/;
	const isEntry = (row: RequestRow) =>
		OWN_PAGE.test(endpointOf(row.url)) &&
		(row.task_kind === 'album' || (row.task_kind === 'artist' && row.task_genius_id === subjectId));
</script>

<!-- The columns have their own widths and do not follow the length of what is in them: the text columns cut with "…". -->
<Table.Root class="table-fixed text-xs">
	<colgroup>
		<col class="w-20" />
		<col class="w-20" />
		<col class="w-1/4" />
		<col />
		<col class="w-24" />
		<col class="w-24" />
	</colgroup>
	<Table.Header>
		<Table.Row>
			<Table.Head>Time</Table.Head>
			<Table.Head>Status</Table.Head>
			<Table.Head>Task</Table.Head>
			<Table.Head>Request</Table.Head>
			{#each SORTABLE as { key, heading } (key)}
				<Table.Head
					aria-sort={sort?.key !== key ? 'none' : sort.dir === 'asc' ? 'ascending' : 'descending'}
				>
					<Button
						variant="ghost"
						title="Sort by {heading.toLowerCase()}"
						onclick={() => (sort = nextSort(sort, key))}
					>
						{heading}
						{#if sort?.key === key}
							{#if sort.dir === 'asc'}<ArrowUp />{:else}<ArrowDown />{/if}
						{/if}
					</Button>
				</Table.Head>
			{/each}
		</Table.Row>
	</Table.Header>
	<Table.Body>
		{#each sorted as row (row.id)}
			{@const name = taskName(row.task_name, row.task_genius_id)}
			<Table.Row data-state={isEntry(row) ? 'selected' : undefined}>
				<Table.Cell class="text-muted-foreground tabular-nums"
					>{clockTime(row.created_at)}</Table.Cell
				>
				<Table.Cell>
					<Badge
						variant={requestTone(row)}
						title={row.error ?? (row.attempt > 1 ? `Attempt ${row.attempt}` : undefined)}
					>
						{row.status_code ?? 'network'}
					</Badge>
				</Table.Cell>
				<Table.Cell class="truncate" title={name}>
					{#if row.page_url}
						<ExtLink href={row.page_url} class="hover:underline">{name}</ExtLink>
					{:else}
						{name}
					{/if}
				</Table.Cell>
				<Table.Cell class="truncate font-mono text-muted-foreground" title={endpointOf(row.url)}>
					<ExtLink href={row.url} class="hover:underline">{endpointOf(row.url)}</ExtLink>
				</Table.Cell>
				<Table.Cell class="font-mono tabular-nums {TOOK[tookTone(row.elapsed_ms)]}">
					{row.elapsed_ms} ms
				</Table.Cell>
				<Table.Cell class="font-mono text-muted-foreground tabular-nums">
					{formatBytes(row.size_bytes)}
				</Table.Cell>
			</Table.Row>
		{:else}
			<Table.Row>
				<Table.Cell colspan={6} class="py-6 text-center text-subtle">{empty}</Table.Cell>
			</Table.Row>
		{/each}
	</Table.Body>
</Table.Root>
