<script lang="ts">
	import { Input } from '#lib/components/ui/input/index.js';
	import { isInvalidDate } from '#lib/utils/partial-date.js';

	// A date as far as it is known: 2012, 2012-10 or 2012-10-22; empty is no date.
	type Props = {
		value: string;
		label: string;
		placeholder?: string;
		disabled?: boolean;
		class?: string;
	};

	let {
		value = $bindable(),
		label,
		placeholder = 'yyyy-mm-dd',
		disabled = false,
		class: className
	}: Props = $props();

	const invalid = $derived(isInvalidDate(value));
</script>

<Input
	bind:value
	aria-label={label}
	aria-invalid={invalid}
	{disabled}
	{placeholder}
	class="w-36 border-transparent tabular-nums {className ?? ''}"
/>
