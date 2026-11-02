<script lang="ts" generics="T extends string">
	import ArrowDown10 from '@lucide/svelte/icons/arrow-down-1-0';
	import ArrowDownAZ from '@lucide/svelte/icons/arrow-down-a-z';
	import ArrowUp01 from '@lucide/svelte/icons/arrow-up-0-1';
	import ArrowUpZA from '@lucide/svelte/icons/arrow-up-z-a';
	import { Button } from '#lib/components/ui/button/index.js';
	import * as Select from '#lib/components/ui/select/index.js';
	import type { Order, SortOption } from '#lib/utils/sort.js';

	type Props = {
		options: SortOption<T>[];
		sort: T;
		order: Order | null; // null: the first direction of the sort
	};

	let { options, sort = $bindable(), order = $bindable() }: Props = $props();

	const current = $derived(options.find((o) => o.value === sort) ?? options[0]);
	const direction = $derived(order ?? current.first);
	// The glyph of the direction follows the kind of the field: numbers and dates count 1-0, names go Z-A, so it is never
	// a second arrow next to the list.
	const Glyph = $derived(
		current.text
			? direction === 'asc'
				? ArrowDownAZ
				: ArrowUpZA
			: direction === 'asc'
				? ArrowUp01
				: ArrowDown10
	);

	// Another field starts from its own side; the button beside the list turns the order around.
	function choose(value: string) {
		sort = value as T;
		order = null;
	}
</script>

<div class="flex h-[24px] items-stretch overflow-hidden rounded-md bg-muted text-xs">
	<Select.Root value={sort} onValueChange={choose}>
		<Select.Trigger
			chevron={false}
			class="h-full w-[77px] justify-start rounded-none border-0 bg-transparent px-2.5 text-xs hover:bg-foreground/15 aria-expanded:bg-foreground/15 focus-visible:shadow-[inset_0_0_0_1px_var(--color-focus)]"
			aria-label="Sort by">{current.label}</Select.Trigger
		>
		<Select.Content>
			{#each options as option (option.value)}
				<Select.Item value={option.value} label={option.label} />
			{/each}
		</Select.Content>
	</Select.Root>
	<Button
		variant="ghost"
		size="icon"
		class="h-full w-[24px] rounded-none px-0 text-foreground/70 hover:bg-foreground/15 hover:text-foreground"
		aria-label={direction === 'asc' ? 'Ascending: reverse' : 'Descending: reverse'}
		onclick={() => (order = direction === 'asc' ? 'desc' : 'asc')}
	>
		<Glyph />
	</Button>
</div>
