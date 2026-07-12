import {defineConfig} from '@playwright/test';
export default defineConfig({testDir:'./e2e',use:{baseURL:process.env.BASE_URL||'http://127.0.0.1:5173',screenshot:'only-on-failure'},reporter:'list'});
