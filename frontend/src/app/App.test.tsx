/** Smoke test that does not require backend or secrets. */
import { describe, expect, it } from 'vitest';
import { App } from './App';
describe('App', () => { it('exports the shell', () => expect(App).toBeTypeOf('function')); });
