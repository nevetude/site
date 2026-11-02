export type Order = 'asc' | 'desc';

/** One kind of sorting for `SortMenu`: `first` is the direction it starts from. */
export type SortOption<T extends string = string> = {
	value: T;
	label: string;
	first: Order;
	text?: true; // sorted by letters: the direction glyph reads A-Z instead of 0-1
};

// The sortings several lists share (the songs, the albums and the clips of an artist).
export const BY_RELEASED = { value: 'released', label: 'Released', first: 'desc' } as const;
export const BY_NAME = { value: 'name', label: 'Alphabet', first: 'asc', text: true } as const;
export const BY_VIEWS = { value: 'views', label: 'Views', first: 'desc' } as const;
