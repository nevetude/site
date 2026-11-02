<script lang="ts" module>
	import { cn, type WithElementRef } from '#lib/utils/cn.js';
	import type { HTMLAnchorAttributes, HTMLButtonAttributes } from 'svelte/elements';

	// One height (28px) for every control. Focus lights the control's own edge (the border is transparent until then).
	const BASE =
		"focus-visible:border-focus aria-invalid:border-destructive rounded-md border border-transparent text-sm font-medium active:not-aria-[haspopup]:translate-y-px [&_svg:not([class*='size-'])]:size-4 group/button inline-flex shrink-0 items-center justify-center whitespace-nowrap transition-colors outline-none select-none disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:shrink-0";

	const VARIANTS = {
		default: 'bg-accent text-foreground hover:bg-foreground/15 aria-expanded:bg-foreground/15',
		ghost:
			'hover:bg-accent hover:text-foreground aria-expanded:bg-accent aria-expanded:text-foreground',
		destructive: 'bg-destructive/15 text-destructive hover:bg-destructive/30',
		// Every close, remove and clear control: grey, red on hover.
		close: 'text-muted-foreground hover:bg-destructive/20 hover:text-destructive'
	} as const;

	const SIZES = { default: 'h-8 gap-2 px-3', icon: 'size-8' } as const;

	export type ButtonVariant = keyof typeof VARIANTS;
	export type ButtonSize = keyof typeof SIZES;

	export const buttonClass = (variant: ButtonVariant = 'default', size: ButtonSize = 'default') =>
		cn(BASE, VARIANTS[variant], SIZES[size]);

	export type ButtonProps = WithElementRef<HTMLButtonAttributes> &
		WithElementRef<HTMLAnchorAttributes> & {
			variant?: ButtonVariant;
			size?: ButtonSize;
		};
</script>

<script lang="ts">
	let {
		class: className,
		variant = 'default',
		size = 'default',
		ref = $bindable(null),
		href = undefined,
		type = 'button',
		disabled,
		children,
		...restProps
	}: ButtonProps = $props();
</script>

{#if href}
	<!-- A link that looks like a button: its address is resolved by the page that uses it. -->
	<!-- eslint-disable svelte/no-navigation-without-resolve -->
	<a
		bind:this={ref}
		data-slot="button"
		class={cn(buttonClass(variant, size), className)}
		href={disabled ? undefined : href}
		aria-disabled={disabled}
		role={disabled ? 'link' : undefined}
		tabindex={disabled ? -1 : undefined}
		{...restProps}
	>
		{@render children?.()}
	</a>
{:else}
	<button
		bind:this={ref}
		data-slot="button"
		class={cn(buttonClass(variant, size), className)}
		{type}
		{disabled}
		{...restProps}
	>
		{@render children?.()}
	</button>
{/if}
