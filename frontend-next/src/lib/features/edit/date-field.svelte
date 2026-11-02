<script lang="ts">
	import ChevronLeft from '@lucide/svelte/icons/chevron-left';
	import ChevronRight from '@lucide/svelte/icons/chevron-right';
	import { Button } from '#lib/components/ui/button/index.js';
	import ResetField from '#lib/features/edit/reset-field.svelte';
	import { isoDay, monthWeeks, shiftMonth } from '#lib/utils/calendar.js';
	import { openPopover } from '#lib/utils/popover.js';

	// A date in the edit mode: it stands as the text it is in the view, and a click opens a calendar in the style of the
	// site, over the page (nothing moves). The calendar picks a whole day: a date known only to the year or the month
	// shows as it is written until a day is picked.
	type Props = { value: string; label: string; edited: boolean; reset: boolean };

	let { value = $bindable(), label, edited, reset = $bindable() }: Props = $props();

	const WEEKDAYS = ['Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa', 'Su'];
	const heading = new Intl.DateTimeFormat('en', {
		month: 'long',
		year: 'numeric',
		timeZone: 'UTC'
	});

	let open = $state(false);
	let trigger = $state<HTMLElement>();
	let el = $state<HTMLElement>();
	// The month the calendar shows: "only the year" and "year and month" take it.
	let shown = $state({ year: 1970, month: 1 });

	const weeks = $derived(monthWeeks(shown.year, shown.month));
	const monthName = $derived(heading.format(new Date(Date.UTC(shown.year, shown.month - 1, 1))));

	// Opens on the month of the date (or its year), and on the current month when there is none.
	function toggle() {
		if (!open) {
			const known = /^(\d{4})(?:-(\d{2}))?/.exec(value);
			const now = new Date();
			shown = known
				? { year: Number(known[1]), month: Number(known[2] ?? 1) }
				: { year: now.getFullYear(), month: now.getMonth() + 1 };
		}
		open = !open;
	}

	$effect(() => {
		if (!open || !el || !trigger) return;
		return openPopover(el, trigger, () => (open = false), false);
	});

	const pick = (text: string) => {
		value = text;
		open = false;
	};
	const move = (step: number) => (shown = shiftMonth(shown.year, shown.month, step));
</script>

<ResetField {edited} bind:reset label="date">
	<button
		bind:this={trigger}
		type="button"
		disabled={reset}
		aria-label="{label}: {value || 'none'}, change"
		aria-haspopup="dialog"
		aria-expanded={open}
		class="-mx-1.5 -my-px rounded-md border border-transparent px-1.5 tabular-nums hover:bg-accent focus-visible:border-focus disabled:opacity-50"
		onclick={toggle}
	>
		{value || '—'}
	</button>
	<div
		bind:this={el}
		popover="manual"
		role="dialog"
		aria-label="Calendar of {label}"
		class="popup p-3"
	>
		<div class="flex items-center justify-between pb-2">
			<Button variant="ghost" size="icon" aria-label="Previous" onclick={() => move(-1)}>
				<ChevronLeft />
			</Button>
			<span class="text-sm font-medium" aria-live="polite">{monthName}</span>
			<Button variant="ghost" size="icon" aria-label="Next" onclick={() => move(1)}>
				<ChevronRight />
			</Button>
		</div>
		<div class="grid grid-cols-7 gap-0.5 text-center">
			{#each WEEKDAYS as weekday (weekday)}
				<span class="flex size-8 items-center justify-center text-xs text-subtle">{weekday}</span>
			{/each}
			{#each weeks as week, i (i)}
				{#each week as day (day.iso)}
					<button
						type="button"
						aria-label={day.iso}
						aria-pressed={day.iso === value}
						class="flex size-8 items-center justify-center rounded-md text-sm transition-colors hover:bg-accent focus-visible:bg-accent aria-pressed:bg-primary aria-pressed:text-primary-foreground {day.inMonth
							? ''
							: 'text-subtle'}"
						onclick={() => pick(day.iso)}
					>
						{day.day}
					</button>
				{/each}
			{/each}
		</div>
		<div class="flex gap-2 pt-2">
			<Button onclick={() => pick(String(shown.year))}>Only {shown.year}</Button>
			<Button onclick={() => pick(isoDay(shown.year, shown.month, 1).slice(0, 7))}>
				{isoDay(shown.year, shown.month, 1).slice(0, 7)}
			</Button>
		</div>
	</div>
</ResetField>
