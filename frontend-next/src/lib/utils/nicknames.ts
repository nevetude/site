import type { NicknameOut } from '#lib/api/client.js';

/** The main names of an artist one after another: each with the year of the release it starts with (none for the first),
 *  in the order of those dates; a name that came back appears again. */
export function nameTimeline(nicknames: NicknameOut[]) {
	return nicknames
		.filter((n) => n.kind === 'main')
		.flatMap((n) =>
			n.periods.map((p) => ({
				name: n.name,
				date: p.start?.release_date ?? null,
				from: p.start?.release_date?.slice(0, 4) ?? null // the year is enough to read a timeline
			}))
		)
		.toSorted((a, b) => (a.date ?? '').localeCompare(b.date ?? ''));
}
