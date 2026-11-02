<script lang="ts">
	type Props = { label: string; done: number; total: number; size?: 'lg' | 'sm' };

	let { label, done, total, size = 'lg' }: Props = $props();
</script>

<div class="min-w-0">
	<div class="text-xs tracking-wider text-muted-foreground uppercase">{label}</div>
	<div
		class="font-semibold tabular-nums {size === 'lg' ? 'text-2xl' : 'text-base'} {done >= total
			? 'text-success'
			: ''}"
	>
		{done}<span class="ml-1 font-normal text-subtle">/ {total}</span>
	</div>
</div>
