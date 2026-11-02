<script lang="ts" module>
	import { getContext, setContext } from 'svelte';

	type Context = { value: string | undefined; pick: (value: string) => void };

	export const setToggleGroup = (ctx: Context) => setContext('toggle-group', ctx);
	export const getToggleGroup = () => getContext<Context>('toggle-group');
</script>

<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { HTMLAttributes } from 'svelte/elements';
	import { cn } from '#lib/utils/cn.js';

	// One of a few values chosen with buttons in a bar (the view of a list). `onValueChange` is told the new value.
	type Props = Omit<HTMLAttributes<HTMLDivElement>, 'role'> & {
		value?: string;
		onValueChange?: (value: string) => void;
		children: Snippet;
	};

	let {
		value = $bindable(),
		onValueChange,
		class: className,
		children,
		...restProps
	}: Props = $props();

	setToggleGroup({
		get value() {
			return value;
		},
		pick(next) {
			value = next;
			onValueChange?.(next);
		}
	});
</script>

<div
	role="group"
	data-slot="toggle-group"
	class={cn(
		'inline-flex h-[24px] w-fit flex-row items-stretch overflow-hidden rounded-md bg-muted',
		className
	)}
	{...restProps}
>
	{@render children()}
</div>
