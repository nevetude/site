<script lang="ts">
	import * as Select from '#lib/components/ui/select/index.js';
	import ResetField from '#lib/features/edit/reset-field.svelte';

	// A choice among a few values (the type of an album, its status), with the button that puts it back to Genius.
	type Props = {
		value: string;
		options: { value: string; label: string }[];
		label: string; // for a screen reader, with a capital letter
		edited: boolean;
		reset: boolean;
		class?: string; // the classes of the trigger
	};

	let {
		value = $bindable(),
		options,
		label,
		edited,
		reset = $bindable(),
		class: className = 'w-40 border-transparent'
	}: Props = $props();
</script>

<ResetField {edited} bind:reset label={label.toLowerCase()}>
	<Select.Root bind:value disabled={reset}>
		<Select.Trigger aria-label={label} class={className}>
			{options.find((option) => option.value === value)?.label}
		</Select.Trigger>
		<Select.Content>
			{#each options as option (option.value)}
				<Select.Item value={option.value} label={option.label} />
			{/each}
		</Select.Content>
	</Select.Root>
</ResetField>
