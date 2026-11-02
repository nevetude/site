<script lang="ts">
	import ImageIcon from '@lucide/svelte/icons/image';
	import { cn } from '#lib/utils/cn.js';

	// What stands in the place of the cover of an album that has none (Genius gives its own picture for that, which is
	// not drawn): a light grey ground with an image icon. It fills the box of the cover; `class` sets the size of the icon.
	let { class: className }: { class?: string } = $props();
</script>

<span class="absolute inset-0 flex items-center justify-center bg-foreground/20" aria-hidden="true">
	<ImageIcon class={cn('size-6 text-foreground/45', className)} />
</span>
