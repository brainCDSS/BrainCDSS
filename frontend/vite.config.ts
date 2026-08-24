// Vite entry; backend traffic remains behind the shared API client.
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
export default defineConfig({ plugins: [react()] });
