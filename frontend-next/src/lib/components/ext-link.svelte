<script lang="ts">
	import type { HTMLAnchorAttributes } from 'svelte/elements';

	let { children, ...restProps }: HTMLAnchorAttributes = $props();
</script>

<!-- The one place for links to other sites (Genius), which the router rule about our own routes does not cover. -->
<!-- eslint-disable svelte/no-navigation-without-resolve -->
<a target="_blank" rel="noreferrer" {...restProps}>{@render children?.()}</a>
