import {defineConfig} from '@playwright/test';
export default defineConfig({
  testDir:'./e2e',
  fullyParallel:false,
  use:{baseURL:process.env.BASE_URL||'http://127.0.0.1:5173',screenshot:'only-on-failure'},
  reporter:'list',
  webServer:{
    command:'docker compose -f ../docker-compose.yml up -d --build',
    url:'http://127.0.0.1:5173',
    timeout:180_000,
    reuseExistingServer:true,
  },
});
