/** Mock remains deterministic and clearly labeled. */
import {expect,it} from 'vitest'; import {MockProvider} from './mock.js';
it('returns mock response',async()=>expect((await new MockProvider().generate({role:'patient',prompt:'x'})).text.startsWith('MOCK:')).toBe(true));
