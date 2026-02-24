import {
  AuthenticationError,
  NotFoundError,
  RateLimitError,
  RemembrError,
  RemembrHttp,
  ServerError,
} from '../src';
import { installMockFetch, installSequentialMockFetch, jsonResponse } from './helpers/mock-fetch';

const ORIGINAL_FETCH = global.fetch;

describe('RemembrHttp', () => {
  afterEach(() => {
    jest.useRealTimers();
    jest.restoreAllMocks();
    global.fetch = ORIGINAL_FETCH;
  });

  test('retries 3 times on 503 before success', async () => {
    jest.useFakeTimers();

    const mock = installSequentialMockFetch([
      jsonResponse({ error: { message: 'unavailable' } }, 503),
      jsonResponse({ error: { message: 'unavailable' } }, 503),
      jsonResponse({ error: { message: 'unavailable' } }, 503),
      jsonResponse({ data: { ok: true } }, 200),
    ]);

    const http = new RemembrHttp({ apiKey: 'k' });
    const promise = http.request<{ ok: boolean }>('GET', '/health');

    await jest.advanceTimersByTimeAsync(7100);
    await expect(promise).resolves.toEqual({ ok: true });
    expect(mock.fetchMock).toHaveBeenCalledTimes(4);
  });

  test('does not retry on 400', async () => {
    const mock = installMockFetch(() => jsonResponse({ error: { message: 'bad request' } }, 400));

    const http = new RemembrHttp({ apiKey: 'k' });
    await expect(http.request('GET', '/bad')).rejects.toBeInstanceOf(RemembrError);
    expect(mock.fetchMock).toHaveBeenCalledTimes(1);
  });

  test('timeout triggers AbortController', async () => {
    jest.useFakeTimers();

    const abortSpy = jest.spyOn(AbortController.prototype, 'abort');
    const mock = installMockFetch((_input, init) => {
      return new Promise<Response>((_resolve, reject) => {
        init?.signal?.addEventListener('abort', () => {
          reject(new DOMException('Aborted', 'AbortError'));
        });
      });
    });

    const http = new RemembrHttp({ apiKey: 'k', timeout: 5 });
    const promise = http.request('GET', '/slow');
    const assertion = expect(promise).rejects.toMatchObject({ name: 'ServerError', code: 'TIMEOUT' });

    await jest.advanceTimersByTimeAsync(8000);

    await assertion;
    expect(abortSpy).toHaveBeenCalled();
    expect(mock.fetchMock).toHaveBeenCalledTimes(4);
  });

  test('response parsing maps all error codes to matching classes', async () => {
    const cases: Array<[number, new (...args: any[]) => Error]> = [
      [401, AuthenticationError],
      [403, AuthenticationError],
      [404, NotFoundError],
      [500, ServerError],
    ];

    for (const [status, ExpectedError] of cases) {
      installMockFetch(() =>
        jsonResponse({ error: { message: `status-${status}`, code: `E${status}` } }, status)
      );

      const http = new RemembrHttp({ apiKey: 'k' });
      if (status >= 500) {
        jest.useFakeTimers();
        const promise = http.request('GET', '/x');
        const assertion = expect(promise).rejects.toBeInstanceOf(ExpectedError);
        await jest.advanceTimersByTimeAsync(7100);
        await assertion;
        jest.useRealTimers();
      } else {
        await expect(http.request('GET', '/x')).rejects.toBeInstanceOf(ExpectedError);
      }
    }
  });

  test('429 maps to RateLimitError after retry behavior', async () => {
    jest.useFakeTimers();

    const mock = installMockFetch(() => jsonResponse({ error: { message: 'rate limited' } }, 429));
    const http = new RemembrHttp({ apiKey: 'k' });

    const promise = http.request('GET', '/limited');
    const assertion = expect(promise).rejects.toBeInstanceOf(RateLimitError);

    await jest.advanceTimersByTimeAsync(7100);
    await assertion;
    expect(mock.fetchMock).toHaveBeenCalledTimes(4);
  });

});
