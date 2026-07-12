import { defineConfig } from 'vite'; import react from '@vitejs/plugin-react';
const proxy={'/api':'http://backend:8000','/healthz':'http://backend:8000'};
export default defineConfig({plugins:[react()],server:{proxy},preview:{proxy}});
