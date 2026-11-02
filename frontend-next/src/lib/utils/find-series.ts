import type { ArtistAlbum } from '#lib/api/client.js';

type Found = { name: string; albums: ArtistAlbum[] };

const MARKER = 'part|pt|side|vol(?:ume)?|season|chapter|episode';
const NUMBER_WORD = 'one|two|three|four|five|six|seven|eight|nine|ten';
const NUMBERED_VARIANT = /^[ivx\d-]+$/i; // "II", "5", "1989-1990": a part of a series, not a "Clean Version"
// A word that numbers a release, what follows the shared start of a series: "Part", "Season", "Pt." and then "IX", "2",
// "One".
const NUMBERING = new RegExp(`^(?:\\d+|[ivx]+|${NUMBER_WORD}|${MARKER})$`);

// What is left at the end of a name when the number is cut off: "Greatest Hits," is "Greatest Hits".
const tidy = (text: string) => text.replace(/[\s,;:\-–—]+$/, '');

// `$` stands for S in the stage names ("$uicide"), so the spellings of one name meet.
const key = (text: string) =>
	text
		.toLowerCase()
		.replaceAll('$', 's')
		.replace(/[^\p{L}\p{N} ]/gu, '')
		.replace(/\s+/g, ' ')
		.trim();

/**
 * By the start of the title: releases whose titles begin with the same two words or more are a series when some of
 * them go on with a number ("Blood Shore" + "Season 1", "Greatest Hits" + "Pt. 2"). Two titles that only begin alike
 * ("Shut Up Listen", "Shut Up Be Quiet") are not: nothing numbers them. The name is the shared start without the word
 * that numbers it. A start of one word is taken only when a title is that word alone ("Taxi") and another one numbers
 * it at once ("Taxi II"): a single shared word ("The") says nothing.
 */
function byStart(albums: ArtistAlbum[]): Found[] {
	const all = albums.map((album) => ({
		album,
		words: album.base_name
			.split(/\s+/)
			.map((word) => ({ word, key: key(word) }))
			.filter((w) => w.key)
	}));
	const titles = all.filter((title) => title.words.length >= 2);

	const clusters = new Map<string, typeof titles>();
	for (const title of titles) {
		const start = `${title.words[0].key} ${title.words[1].key}`;
		clusters.set(start, [...(clusters.get(start) ?? []), title]);
	}

	const byPair = [...clusters.values()].flatMap((cluster) => {
		if (cluster.length < 2) return [];
		let common = cluster[0].words.map((w) => w.key);
		for (const { words } of cluster) {
			const same = common.findIndex((k, i) => words[i]?.key !== k);
			if (same !== -1) common = common.slice(0, same);
		}
		const numbered = cluster.some(({ words }) =>
			words.slice(common.length).some((w) => NUMBERING.test(w.key))
		);
		if (!numbered) return [];
		let end = common.length;
		while (end > 1 && NUMBERING.test(common[end - 1])) end--;
		const name = tidy(
			cluster[0].words
				.slice(0, end)
				.map((w) => w.word)
				.join(' ')
		);
		return [{ name, albums: cluster.map((title) => title.album) }];
	});

	const words = new Map<string, typeof all>();
	for (const title of all.filter((t) => t.words.length)) {
		words.set(title.words[0].key, [...(words.get(title.words[0].key) ?? []), title]);
	}
	const byWord = [...words.values()].flatMap((cluster) => {
		const bare = cluster.filter((title) => title.words.length === 1);
		const numbered = cluster.filter(
			(title) => title.words.length > 1 && NUMBERING.test(title.words[1].key)
		);
		if (!bare.length || !numbered.length) return [];
		return [
			{
				name: tidy(bare[0].words[0].word),
				albums: [...bare, ...numbered].map((title) => title.album)
			}
		];
	});

	return [...byPair, ...byWord];
}

/**
 * Looks for series among the releases of one artist by the start of their titles. Two or more different releases make
 * a series (the same title with only "Clean Version" as the difference does not).
 */
export function findSeries(albums: ArtistAlbum[]): Found[] {
	return byStart(albums)
		.filter((group) => {
			const parts = group.albums.map(
				(a) => `${a.base_name}|${a.variant && NUMBERED_VARIANT.test(a.variant) ? a.variant : ''}`
			);
			return new Set(parts).size > 1;
		})
		.map((group) => ({
			...group,
			albums: group.albums.toSorted(
				(a, b) => (a.release_date ?? '9999').localeCompare(b.release_date ?? '9999') || a.id - b.id
			)
		}));
}
