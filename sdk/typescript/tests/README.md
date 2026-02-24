# TypeScript SDK Tests

## Running tests

From `sdk/typescript/`:

- `npm test` — runs TypeScript type-check (`tsc --noEmit`) then Jest with coverage.
- `npm run build` — compiles the SDK to `dist/`.

## Notes

- All tests mock `fetch`; no real Remembr API requests are made.
- Coverage reports are generated in `sdk/typescript/coverage/`.
