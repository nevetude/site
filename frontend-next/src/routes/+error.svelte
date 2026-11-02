<script lang="ts">
	import { page } from '$app/state';
</script>

<p class="text-sm {page.status === 404 ? 'text-muted-foreground' : 'text-destructive'}">
	{page.error?.message}
</p>
