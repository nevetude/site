<script lang="ts" module>
	// The look of a chip of a filter, the same as on the first version of the site: a filled tile that lights up when on.
	export const chip = (on: boolean) =>
		`rounded-md px-2.5 py-1 text-[13px] outline-none focus-visible:shadow-[inset_0_0_0_1px_var(--color-focus)] ${on ? 'bg-foreground/15 text-foreground' : 'bg-muted text-foreground/60 hover:text-foreground'}`;
</script>

<script lang="ts">
	import type { Snippet } from 'svelte';

	// The roles to filter a list by; all the selected ones must match. The first `visible` roles are shown, the rest
	// open with "+N more".
	type Props = {
		roles: { role: string; count: number }[];
		selected: string[];
		visible?: number;
		end?: Snippet; // pushed to the right end of the row
	};

	let { roles, selected = $bindable(), visible = 10, end }: Props = $props();

	let all = $state(false);
	const shown = $derived(all ? roles : roles.slice(0, visible));

	const toggle = (role: string) =>
		(selected = selected.includes(role) ? selected.filter((r) => r !== role) : [...selected, role]);
</script>

{#if roles.length || end}
	<div class="flex flex-wrap items-center gap-1.5">
		{#each shown as { role, count } (role)}
			{@const on = selected.includes(role)}
			<button type="button" aria-pressed={on} class={chip(on)} onclick={() => toggle(role)}>
				{role}
				<span class="font-mono text-foreground/40 tabular-nums">{count}</span>
			</button>
		{/each}
		{#if roles.length > visible}
			<button
				type="button"
				aria-expanded={all}
				class="px-1 text-[13px] text-foreground/50 hover:text-foreground"
				onclick={() => (all = !all)}
			>
				{all ? 'less' : `+${roles.length - visible} more`}
			</button>
		{/if}
		{#if end}<div class="ml-auto">{@render end()}</div>{/if}
	</div>
{/if}
