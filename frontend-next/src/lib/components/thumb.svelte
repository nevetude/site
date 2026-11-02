<script lang="ts">
	import { cn } from '#lib/utils/cn.js';

	// A picture, or the first letter of `name` when there is none (an empty name: a blank square). Square with soft
	// corners like the covers; `class` sets the size and, when a place wants it, `rounded-full`. The picture is a plain
	// `<img>` on top of the letter, so a native `loading="lazy"` fetches what is near the screen and a list of a hundred
	// rows does not load a hundred pictures at once. The letter stays under a picture that has not come yet or has failed.
	type Props = { src: string | null; name: string; class?: string };

	let { src, name, class: className }: Props = $props();

	let failed = $state(false);
</script>

<span
	class={cn(
		// The thin rim over the picture (the `after` box) is what the covers had before: it keeps a dark cover from melting into the card.
		'relative flex size-14 shrink-0 items-center justify-center overflow-hidden rounded-lg bg-muted text-sm text-muted-foreground select-none after:absolute after:inset-0 after:rounded-[inherit] after:border after:border-border after:mix-blend-lighten',
		className
	)}
>
	{name.slice(0, 1).toUpperCase()}
	{#if src && !failed}
		<img
			{src}
			alt=""
			loading="lazy"
			decoding="async"
			class="absolute inset-0 size-full object-cover"
			onerror={() => (failed = true)}
		/>
	{/if}
</span>
