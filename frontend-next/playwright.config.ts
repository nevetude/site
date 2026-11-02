import { defineConfig } from '@playwright/test';

export default defineConfig({
	// A server that already runs on 8081 (the dev one) is used as it is.
	webServer: { command: 'pnpm build && pnpm preview', port: 8081, reuseExistingServer: true },
	use: { baseURL: 'http://localhost:8081' },
	testMatch: '**/*.e2e.ts'
});
