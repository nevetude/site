import { expect, test, type Page } from '@playwright/test';
import type { AlbumDetail, ArtistDetail, SongDetail } from '#lib/api/client.js';

// The API is answered here, not by the backend: the pages are opened in the edit mode, a field is changed, and what the
// page sends on Save is what is looked at. (The fixtures are typed with the generated types, so they follow the API.)

const when = '2026-01-01T00:00:00Z';
const ann = {
	id: 1,
	genius_id: 11,
	base_name: 'Ann',
	cover_url: null,
	artist_type: 'person' as const,
	import_state: 'full' as const
};

const album: AlbumDetail = {
	id: 7,
	genius_id: 70,
	name: 'Record',
	base_name: 'Record',
	variant: 'Deluxe',
	disambiguator: null,
	album_type: 'album',
	import_state: 'full',
	language: null,
	release_date: '2012-10-22',
	release_date_precision: 'day',
	is_released: true,
	description: 'By Genius',
	description_dom: null,
	description_refs: [],
	genius_url: null,
	cover_url: null,
	cover_thumbnail_url: null,
	cover_primary_color: null,
	cover_secondary_color: null,
	created_at: when,
	updated_at: when,
	artists: [ann],
	covers: [],
	edited: [],
	tracks_count: 1,
	discs_count: 1,
	genres: [],
	tags: [],
	credits: [],
	related: [],
	imports: [],
	history: []
};

const artist: ArtistDetail = {
	id: 1,
	genius_id: 11,
	name: 'Ann',
	base_name: 'Ann',
	disambiguator: null,
	artist_type: 'group',
	import_state: 'full',
	description: 'A group',
	genius_url: null,
	cover_url: null,
	is_verified: false,
	is_meme_verified: false,
	followers_count: 5,
	created_at: when,
	updated_at: when,
	description_dom: null,
	description_refs: [],
	real_name: null,
	born: null,
	died: null,
	links: [],
	aliases: ['Annie'],
	nicknames: [],
	edited: [],
	members: [
		{
			artist: { ...ann, id: 2, base_name: 'Bob' },
			starts_on: '2012-01-01',
			starts_precision: 'year',
			ends_on: null,
			ends_precision: null,
			has_left: false,
			start: null,
			end: null
		}
	],
	groups: [],
	songs_count: 0,
	albums_count: 0,
	song_roles: [],
	album_roles: [],
	series: [],
	genres: [],
	imports: [],
	history: []
};

const song: SongDetail = {
	id: 5,
	genius_id: 50,
	name: 'Tune',
	base_name: 'Tune',
	variant: null,
	disambiguator: null,
	import_state: 'full',
	language: null,
	release_date: '2020-05-17',
	release_date_precision: 'day',
	description: null,
	description_dom: null,
	description_refs: [],
	recording_location: null,
	explicit: false,
	instrumental: false,
	lyrics_state: null,
	genius_url: null,
	cover_url: null,
	cover_thumbnail_url: null,
	cover_primary_color: null,
	cover_secondary_color: null,
	view_count: null,
	genre: 'Rap',
	tags: ['rap'],
	artists: [ann],
	featured: [],
	credits: [],
	albums: [],
	related: [],
	videos: [],
	audios: [],
	created_at: when,
	updated_at: when,
	imports: [],
	history: [],
	edited: []
};

/** Answers the API of one page; returns the bodies of the writes it got, by method and path. */
async function serve(page: Page, answers: Record<string, unknown>) {
	const writes: Record<string, unknown> = {};
	await page.route('**/api/v1/**', (route) => {
		const request = route.request();
		const path = new URL(request.url()).pathname.replace('/api/v1', '');
		if (path === '/me') {
			return route.fulfill({ json: { id: 1, login: 'admin', role: 'admin', can_edit: true } });
		}
		if (request.method() !== 'GET') {
			writes[`${request.method()} ${path}`] = request.postDataJSON();
			return route.fulfill({ json: answers[path] ?? {} });
		}
		return route.fulfill({ json: answers[path] ?? [] });
	});
	return writes;
}

test('an album is edited in place: the fields that were changed are sent, and only those', async ({
	page
}) => {
	const writes = await serve(page, {
		'/albums/7': album,
		'/albums/7/tracks': [],
		'/albums/7/videos': []
	});
	await page.goto('/albums/7');
	await page.getByRole('button', { name: 'Edit the page' }).click();

	await page.getByLabel('Title', { exact: true }).fill('Record, again');
	await page.getByRole('button', { name: /^Release date/ }).click();
	await page.getByRole('button', { name: 'Next', exact: true }).click();
	await page.getByRole('button', { name: /^\d{4}-\d{2}$/ }).click(); // the year and the month the calendar shows
	await page.getByRole('button', { name: 'Save', exact: true }).click();

	await expect
		.poll(() => writes['PATCH /albums/7'])
		.toEqual({
			base_name: 'Record, again',
			release_date: '2012-11-01',
			release_date_precision: 'month'
		});
	expect(Object.keys(writes)).toEqual(['PATCH /albums/7']); // the tracks and the credits were not changed
});

test('Cancel leaves the page as it was, and sends nothing', async ({ page }) => {
	const writes = await serve(page, {
		'/albums/7': album,
		'/albums/7/tracks': [],
		'/albums/7/videos': []
	});
	await page.goto('/albums/7');
	await page.getByRole('button', { name: 'Edit the page' }).click();
	await page.getByLabel('Title', { exact: true }).fill('Typed and dropped');

	await page.getByRole('button', { name: 'Cancel' }).click();

	await expect(page.getByRole('heading', { level: 1 })).toContainText('Record');
	expect(writes).toEqual({});
});

test('an artist gets a main name, an alter ego from an alias and the time of a member', async ({
	page
}) => {
	const writes = await serve(page, { '/artists/1': artist });
	await page.goto('/artists/1');
	await page.getByRole('button', { name: 'Edit the page' }).click();

	await page.getByLabel('Real name', { exact: true }).fill('Anna Roe');
	await page.getByLabel('Main name', { exact: true }).fill('Ann Roe'); // the name of the page is in the list already
	await page.getByLabel('Disambiguator').fill('UK');
	// An alias of Genius is dragged into the list of the alter egos.
	await page
		.getByRole('listitem')
		.filter({ hasText: 'Annie' })
		.dragTo(page.getByRole('heading', { name: 'Alter egos' }));
	await page.getByLabel('Start of Bob').fill('2010');
	await page.getByRole('button', { name: 'Save', exact: true }).click();

	await expect
		.poll(() => writes['PATCH /artists/1'])
		.toEqual({ disambiguator: 'UK', real_name: 'Anna Roe' });
	await expect
		.poll(() => writes['PUT /artists/1/nicknames'])
		.toEqual([
			{ kind: 'main', name: 'Ann Roe', spellings: [], periods: [{}], uses: [] },
			{ kind: 'alter_ego', name: 'Annie', spellings: [], periods: [], uses: [] }
		]);
	await expect
		.poll(() => writes['PUT /artists/1/members'])
		.toEqual([
			{ member_id: 2, start: { date: '2010-01-01', precision: 'year' }, end: null, has_left: false }
		]);
});

test('an artist gets a series, and a release is found by name and put into it', async ({
	page
}) => {
	const found = {
		id: 7,
		base_name: 'Record',
		variant: null,
		album_type: 'album',
		release_date: '2012-11-01',
		release_date_precision: 'day',
		is_released: true,
		cover_thumbnail_url: null,
		tracks_count: 1,
		view_count: null,
		import_state: 'full',
		artists: ['Ann'],
		labels: [],
		roles: []
	};
	const writes = await serve(page, {
		'/artists/1': artist,
		'/artists/1/albums': { items: [found], total: 1 }
	});
	await page.goto('/artists/1');
	await page.getByRole('button', { name: 'Edit the page' }).click();

	await page.getByLabel('Name of the series').fill('Records');
	await page.getByRole('button', { name: 'Release', exact: true }).click();
	await expect(page.getByRole('list', { name: 'Found' })).toBeVisible(); // the newest ones are listed at once
	await page.getByLabel('Find a release to add').fill('Rec');
	await page
		.getByRole('list', { name: 'Found' })
		.getByRole('button', { name: /Record/ })
		.click();
	await page.getByRole('button', { name: 'Save', exact: true }).click();

	await expect
		.poll(() => writes['PUT /artists/1/series'])
		.toEqual([{ name: 'Records', album_ids: [7] }]);
});

test('Find series puts the releases with a shared title into a series', async ({ page }) => {
	const part = (id: number, base_name: string) => ({
		id,
		base_name,
		variant: null,
		album_type: 'ep',
		release_date: `2014-0${id}-01`,
		release_date_precision: 'day',
		is_released: true,
		cover_thumbnail_url: null,
		tracks_count: 1,
		view_count: null,
		import_state: 'full',
		artists: ['Ann'],
		labels: [],
		roles: []
	});
	const items = [part(1, 'Saga Part I: One'), part(2, 'Saga Part II: Two'), part(3, 'Alone')];
	const writes = await serve(page, {
		'/artists/1': artist,
		'/artists/1/albums': { items, total: 3 }
	});
	await page.goto('/artists/1');
	await page.getByRole('button', { name: 'Edit the page' }).click();

	await page.getByRole('button', { name: 'Find series' }).click();
	await page.getByRole('button', { name: 'Save', exact: true }).click();

	await expect
		.poll(() => writes['PUT /artists/1/series'])
		.toEqual([{ name: 'Saga', album_ids: [1, 2] }]);
});

test('a song gets a genre, a tag and a guest', async ({ page }) => {
	const writes = await serve(page, {
		'/songs/5': song,
		'/songs/5/lyrics': null,
		'/genres': { id: 9, name: 'Phonk' },
		'/artists/search': [{ ...ann, id: 3, base_name: 'Cat' }]
	});
	await page.goto('/songs/5');
	await page.getByRole('button', { name: 'Edit the page' }).click();

	await page.getByLabel('Genre', { exact: true }).fill('Phonk');
	await page.getByLabel('the tags', { exact: true }).fill('trap');
	await page.getByLabel('the tags', { exact: true }).press('Enter');
	await page.getByLabel('Add to the guests').fill('cat');
	await page.getByRole('list', { name: 'Found' }).getByRole('button').first().click();
	await page.getByRole('button', { name: 'Save', exact: true }).click();

	await expect.poll(() => writes['PUT /songs/5/tags']).toEqual(['rap', 'trap']);
	await expect.poll(() => writes['PATCH /songs/5']).toEqual({ genre_id: 9 });
	await expect.poll(() => writes['PUT /songs/5/artists']).toEqual({ artists: [1], featured: [3] });
});
