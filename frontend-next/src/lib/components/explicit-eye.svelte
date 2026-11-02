<script lang="ts">
	import EyeOff from '@lucide/svelte/icons/eye-off';
	import { cn } from '#lib/utils/cn.js';

	// The crossed eye over a cover that is marked explicit (the cover under it is blurred a little by the place). Grey, and
	// lighter when the pointer is on the thing the cover belongs to: the place says on what, with `class`
	// (`group-hover:text-white/90`), and sets a size for a small cover.
	let { class: className }: { class?: string } = $props();
</script>

<span class="absolute inset-0 flex items-center justify-center bg-black/20" aria-hidden="true">
	<EyeOff class={cn('size-6 text-white/50 transition-colors duration-200 ease-out', className)} />
</span>
