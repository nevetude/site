import { expect, test } from '@playwright/test';

test('the import page opens with the discography mode and its search', async ({ page }) => {
	await page.goto('/import');
	await expect(page.getByLabel('Find an artist')).toBeVisible();
	await expect(page.getByLabel('Artist id')).toBeVisible();
	await expect(page.getByLabel('Albums limit')).toBeVisible();
	await expect(page.getByRole('heading', { name: 'Monitor' })).toBeVisible();
});

test('one entity is imported by its id from the mode menu', async ({ page }) => {
	await page.goto('/import');
	await page.waitForLoadState('networkidle'); // clicks before hydration do nothing
	await page.getByLabel('Mode').click();
	await page.getByRole('option', { name: 'albums/{id}' }).click();
	await expect(page.getByLabel('Find an artist')).toBeHidden();
	await expect(page.getByLabel('Albums limit')).toBeHidden();
	const start = page.getByRole('button', { name: 'Import', exact: true });
	await expect(start).toBeDisabled();
	await page.getByLabel('Id', { exact: true }).fill('1460125');
	await expect(start).toBeEnabled();
});

test('a group shows its members before the import, and the list can be changed', async ({
	page
}) => {
	const member = (genius_id: number, name: string) => ({
		genius_id,
		name,
		image_url: null,
		source: 'genius'
	});
	await page.route('**/api/v1/groups/10', (route) =>
		route.fulfill({
			json: {
				genius_id: 10,
				name: 'Band',
				saved: false,
				discographies: false,
				members: [member(1, 'Ann'), member(2, 'Bob')]
			}
		})
	);
	await page.goto('/import');
	await page.waitForLoadState('networkidle');
	await expect(page.getByRole('list', { name: 'Members of the group' })).toBeHidden();

	await page.getByLabel('Artist id').fill('10');
	const members = page.getByRole('list', { name: 'Members of the group' }).getByRole('listitem');
	await expect(members).toHaveCount(2);
	await page.getByRole('button', { name: 'Take Bob out of the group' }).click();
	await expect(members).toHaveCount(1);

	// The import carries the settled list and the choice of the discographies.
	let body: { group?: { discographies: boolean; members: unknown[] } } = {};
	await page.route('**/api/v1/imports', (route) => {
		if (route.request().method() !== 'POST') return route.fallback();
		body = route.request().postDataJSON();
		return route.fulfill({ status: 202, json: {} });
	});
	await page.getByRole('checkbox', { name: 'Discographies of the members' }).click();
	await page.getByRole('button', { name: 'Import', exact: true }).click();
	await expect.poll(() => body.group?.discographies).toBe(true);
	expect(body.group?.members).toHaveLength(1);
});

test('the monitor shows the server only when it is opened', async ({ page }) => {
	await page.goto('/import');
	await page.waitForLoadState('networkidle');
	await expect(page.getByRole('heading', { name: 'Server' })).toBeHidden();
	await page.getByRole('button', { name: 'More' }).click();
	await expect(page.getByRole('heading', { name: 'Server' })).toBeVisible();
});
