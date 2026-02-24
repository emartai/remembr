export type FetchHandler = (
  input: RequestInfo | URL,
  init?: RequestInit
) => Promise<Response> | Response;

export interface MockFetchController {
  fetchMock: jest.MockedFunction<typeof fetch>;
  calls: Array<{ input: RequestInfo | URL; init?: RequestInit }>;
  restore: () => void;
}

export function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

export function installMockFetch(handler: FetchHandler): MockFetchController {
  const originalFetch = global.fetch;
  const calls: Array<{ input: RequestInfo | URL; init?: RequestInit }> = [];

  const fetchMock = jest.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    calls.push({ input, init });
    return handler(input, init);
  }) as jest.MockedFunction<typeof fetch>;

  global.fetch = fetchMock;

  return {
    fetchMock,
    calls,
    restore: () => {
      global.fetch = originalFetch;
    },
  };
}

export function installSequentialMockFetch(responses: Array<Response | FetchHandler>): MockFetchController {
  let index = 0;
  return installMockFetch(async (input, init) => {
    const current = responses[Math.min(index, responses.length - 1)];
    index += 1;
    if (typeof current === 'function') {
      return current(input, init);
    }
    return current;
  });
}
