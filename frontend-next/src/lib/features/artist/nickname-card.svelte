<script lang="ts">
	import Plus from '@lucide/svelte/icons/plus';
	import X from '@lucide/svelte/icons/x';
	import type { ReleaseRef } from '#lib/api/client.js';
	import { Button } from '#lib/components/ui/button/index.js';
	import { Input } from '#lib/components/ui/input/index.js';
	import * as Select from '#lib/components/ui/select/index.js';
	import type { DraftNickname } from '#lib/features/artist/artist-draft.svelte.js';
	import ReleaseField from '#lib/features/edit/release-field.svelte';

	// One name of an artist. A main name has its periods (it starts with a release; the first one with none is the name
	// from the beginning) and may have a spelling chosen on some releases. An alter ego has the releases it is the name
	// on, and where there: as an artist, in the credits, or in both (so one release can show the main name as its artist and
	// an alter ego as its producer). Every name has spellings: ways to write it that mean the same name.
	type Props = { nickname: DraftNickname; artistId: number; onremove: () => void };

	let { nickname = $bindable(), artistId, onremove }: Props = $props();

	const SCOPES = [
		{ value: 'any', label: 'Everywhere' },
		{ value: 'artist', label: 'As an artist' },
		{ value: 'credit', label: 'In the credits' }
	] as const;

	let spelling = $state('');
	let release = $state<ReleaseRef | null>(null);

	function addSpelling() {
		const text = spelling.trim();
		if (text && text !== nickname.name && !nickname.spellings.includes(text)) {
			nickname.spellings.push(text);
		}
		spelling = '';
	}

	function removeSpelling(text: string) {
		nickname.spellings = nickname.spellings.filter((s) => s !== text);
		for (const use of nickname.uses) if (use.spelling === text) use.spelling = '';
	}

	// A release that was picked becomes a row of the list, and the field is empty again for the next one.
	$effect(() => {
		if (!release) return;
		nickname.uses.push({ release, spelling: '', scope: 'any' });
		release = null;
	});
</script>

<div class="space-y-3 rounded-lg bg-muted/40 p-3 transition-colors duration-200 hover:bg-muted/70">
	<div class="flex items-center gap-2">
		<Input
			bind:value={nickname.name}
			aria-label={nickname.kind === 'main' ? 'Main name' : 'Alter ego'}
			placeholder={nickname.kind === 'main' ? 'name' : 'alter ego'}
			class="border-transparent font-medium"
		/>
		<Button
			variant="close"
			size="icon"
			aria-label="Take away {nickname.name || 'this name'}"
			onclick={onremove}
		>
			<X />
		</Button>
	</div>

	{#if nickname.kind === 'main'}
		<ul class="space-y-1.5" aria-label="Periods of {nickname.name}">
			{#each nickname.periods as period, i (i)}
				<li class="flex flex-wrap items-center gap-2 text-sm">
					<ReleaseField
						{artistId}
						bind:release={period.start}
						label="Release the period of {nickname.name} starts with"
						placeholder="starts with a release"
					/>
					{#if nickname.periods.length > 1}
						<Button
							variant="close"
							size="icon"
							aria-label="Take away this period"
							onclick={() => nickname.periods.splice(i, 1)}
						>
							<X />
						</Button>
					{/if}
				</li>
			{/each}
		</ul>
		<Button
			variant="ghost"
			class="text-muted-foreground"
			onclick={() => nickname.periods.push({ start: null })}
		>
			<Plus /> another period
		</Button>
	{/if}

	<div class="flex flex-wrap items-center gap-1.5" aria-label="Spellings of {nickname.name}">
		{#each nickname.spellings as text (text)}
			<span class="inline-flex items-center gap-1 rounded-md bg-muted px-2 py-0.5 text-xs">
				{text}
				<button
					type="button"
					class="text-subtle hover:text-destructive"
					aria-label="Take away the spelling {text}"
					onclick={() => removeSpelling(text)}
				>
					<X class="size-3" />
				</button>
			</span>
		{/each}
		<Input
			bind:value={spelling}
			aria-label="Add a spelling of {nickname.name}"
			placeholder="a spelling, for example BLADEE"
			onkeydown={(e) => e.key === 'Enter' && (e.preventDefault(), addSpelling())}
			onblur={addSpelling}
			class="h-7 w-56 border-transparent text-xs"
		/>
	</div>

	<div class="space-y-1.5">
		<ul class="space-y-1.5" aria-label="Releases of {nickname.name}">
			{#each nickname.uses as use, i (i)}
				<li class="flex flex-wrap items-center gap-2">
					<ReleaseField {artistId} release={use.release} label="Release" removable={false} />
					{#if nickname.spellings.length}
						<Select.Root bind:value={use.spelling}>
							<Select.Trigger
								aria-label="Spelling on {use.release.name}"
								class="h-7 w-40 border-transparent text-xs"
							>
								{use.spelling || nickname.name}
							</Select.Trigger>
							<Select.Content>
								<Select.Item value="" label={nickname.name} />
								{#each nickname.spellings as text (text)}
									<Select.Item value={text} label={text} />
								{/each}
							</Select.Content>
						</Select.Root>
					{/if}
					{#if nickname.kind === 'alter_ego'}
						<Select.Root bind:value={use.scope}>
							<Select.Trigger
								aria-label="Where {nickname.name} is the name on {use.release.name}"
								class="h-7 w-36 border-transparent text-xs"
							>
								{SCOPES.find((s) => s.value === use.scope)?.label}
							</Select.Trigger>
							<Select.Content>
								{#each SCOPES as scope (scope.value)}
									<Select.Item value={scope.value} label={scope.label} />
								{/each}
							</Select.Content>
						</Select.Root>
					{/if}
					<Button
						variant="close"
						size="icon"
						aria-label="Take {use.release.name} away"
						onclick={() => nickname.uses.splice(i, 1)}
					>
						<X />
					</Button>
				</li>
			{/each}
		</ul>
		<ReleaseField
			{artistId}
			bind:release
			label="Add a release for {nickname.name}"
			placeholder="add a release"
		/>
	</div>
</div>
