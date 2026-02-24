import { AuthenticationError, ServerError } from './errors';
import { RemembrHttp } from './http';
import {
  CheckpointInfo,
  Episode,
  ListSessionsParams,
  MemoryQueryResult,
  RemembrConfig,
  SearchMemoryParams,
  Session,
  StoreMemoryParams,
} from './types';

const VALID_SEARCH_MODES = new Set(['semantic', 'hybrid', 'filter_only']);

interface RestoreResponse {
  restoredMessageCount: number;
}

interface ForgetEpisodeResponse {
  deleted: boolean;
}

interface ForgetSessionResponse {
  deletedCount: number;
}

interface ForgetUserResponse {
  deletedEpisodes: number;
  deletedSessions: number;
}

/** Remembr API client exposing session, memory, checkpoint, and forget operations. */
export class RemembrClient {
  private readonly http: RemembrHttp;

  constructor(config: RemembrConfig = {}) {
    const apiKey = config.apiKey ?? this.getApiKeyFromEnv();
    if (!apiKey) {
      throw new AuthenticationError(
        'Missing API key. Pass `apiKey` or set REMEMBR_API_KEY environment variable.'
      );
    }

    this.http = new RemembrHttp({ ...config, apiKey });
  }

  /**
   * Create a new memory session.
   * @param metadata Optional metadata dictionary stored alongside the created session.
   */
  async createSession(metadata?: Record<string, unknown>): Promise<Session> {
    const data = await this.http.request<Session>('POST', '/sessions', {
      body: { metadata: metadata ?? {} },
    });
    return data;
  }

  /**
   * Fetch metadata for a single session.
   * @param sessionId The session identifier.
   */
  async getSession(sessionId: string): Promise<Session> {
    this.requireNonEmpty(sessionId, 'sessionId');

    const data = await this.http.request<Record<string, unknown>>('GET', `/sessions/${sessionId}`);
    const session = data.session as Record<string, unknown> | undefined;

    if (!session || typeof session !== 'object') {
      throw new ServerError('Invalid session payload returned by Remembr API.');
    }

    return {
      request_id: String(data.request_id ?? ''),
      session_id: String(session.session_id ?? ''),
      org_id: String(session.org_id ?? ''),
      created_at: String(session.created_at ?? ''),
      metadata: (session.metadata as Record<string, unknown> | null | undefined) ?? null,
    };
  }

  /**
   * List sessions for the authenticated scope.
   * @param params Pagination options.
   */
  async listSessions(): Promise<Session[]>;
  async listSessions(params: ListSessionsParams): Promise<Session[]>;
  async listSessions(params: ListSessionsParams = {}): Promise<Session[]> {
    const limit = params.limit ?? 20;
    const offset = params.offset ?? 0;
    this.validatePagination(limit, offset);

    const data = await this.http.request<Record<string, unknown>>('GET', '/sessions', {
      params: { limit, offset },
    });

    const sessions = Array.isArray(data.sessions) ? data.sessions : [];
    const requestId = String(data.request_id ?? '');
    const orgId = String(data.org_id ?? '');

    return sessions
      .filter((session) => typeof session === 'object' && session !== null)
      .map((session) => {
        const s = session as Record<string, unknown>;
        return {
          request_id: requestId,
          session_id: String(s.session_id ?? ''),
          org_id: orgId,
          created_at: String(s.created_at ?? ''),
          metadata: (s.metadata as Record<string, unknown> | null | undefined) ?? null,
        };
      });
  }

  /**
   * Store a memory episode.
   * @param params Memory payload to persist.
   */
  async store(params: StoreMemoryParams): Promise<Episode> {
    this.requireNonEmpty(params.content, 'content');
    const role = params.role ?? 'user';
    this.requireNonEmpty(role, 'role');

    if (params.sessionId) {
      this.requireNonEmpty(params.sessionId, 'sessionId');
    }

    const data = await this.http.request<Record<string, unknown>>('POST', '/memory', {
      body: {
        content: params.content,
        role,
        session_id: params.sessionId,
        tags: params.tags ?? [],
        metadata: params.metadata ?? {},
      },
    });

    return {
      episode_id: String(data.episode_id ?? ''),
      session_id: (data.session_id as string | null | undefined) ?? null,
      role,
      content: params.content,
      created_at: String(data.created_at ?? ''),
      tags: params.tags ?? [],
      metadata: params.metadata ?? null,
    };
  }

  /**
   * Search memory episodes.
   * @param params Search filters and query options.
   */
  async search(params: SearchMemoryParams): Promise<MemoryQueryResult> {
    this.requireNonEmpty(params.query, 'query');

    const mode = params.mode ?? 'hybrid';
    if (!VALID_SEARCH_MODES.has(mode)) {
      throw new Error('mode must be one of: semantic, hybrid, filter_only');
    }

    const limit = params.limit ?? 20;
    if (limit < 1) {
      throw new Error('limit must be greater than 0');
    }

    if (params.sessionId) {
      this.requireNonEmpty(params.sessionId, 'sessionId');
    }

    if (params.fromTime && params.toTime && params.fromTime > params.toTime) {
      throw new Error('fromTime must be less than or equal to toTime');
    }

    const data = await this.http.request<MemoryQueryResult>('POST', '/memory/search', {
      body: {
        query: params.query,
        session_id: params.sessionId,
        tags: params.tags,
        from_time: params.fromTime?.toISOString(),
        to_time: params.toTime?.toISOString(),
        limit,
        mode,
      },
    });

    return data;
  }

  /**
   * Get a session's memory history.
   * @param sessionId Session identifier.
   * @param params Optional history retrieval options.
   */
  async getSessionHistory(sessionId: string): Promise<Episode[]>;
  async getSessionHistory(sessionId: string, params: { limit?: number }): Promise<Episode[]>;
  async getSessionHistory(sessionId: string, params: { limit?: number } = {}): Promise<Episode[]> {
    this.requireNonEmpty(sessionId, 'sessionId');

    const limit = params.limit ?? 50;
    if (limit < 1) {
      throw new Error('limit must be greater than 0');
    }

    const data = await this.http.request<Record<string, unknown>>('GET', `/sessions/${sessionId}/history`, {
      params: { limit },
    });

    return Array.isArray(data.episodes) ? (data.episodes as Episode[]) : [];
  }

  /**
   * Create a session checkpoint.
   * @param sessionId Session identifier to checkpoint.
   */
  async checkpoint(sessionId: string): Promise<CheckpointInfo> {
    this.requireNonEmpty(sessionId, 'sessionId');
    return this.http.request<CheckpointInfo>('POST', `/sessions/${sessionId}/checkpoint`);
  }

  /**
   * Restore a session to a checkpoint.
   * @param sessionId Session identifier to restore.
   * @param checkpointId Checkpoint identifier to restore from.
   */
  async restore(sessionId: string, checkpointId: string): Promise<RestoreResponse> {
    this.requireNonEmpty(sessionId, 'sessionId');
    this.requireNonEmpty(checkpointId, 'checkpointId');

    return this.http.request<RestoreResponse>('POST', `/sessions/${sessionId}/restore`, {
      body: { checkpoint_id: checkpointId },
    });
  }

  /**
   * List checkpoints for a session.
   * @param sessionId Session identifier to inspect.
   */
  async listCheckpoints(sessionId: string): Promise<CheckpointInfo[]> {
    this.requireNonEmpty(sessionId, 'sessionId');

    const data = await this.http.request<Record<string, unknown>>('GET', `/sessions/${sessionId}/checkpoints`);
    return Array.isArray(data.checkpoints) ? (data.checkpoints as CheckpointInfo[]) : [];
  }

  /**
   * Delete a single memory episode.
   * @param episodeId Episode identifier to delete.
   */
  async forgetEpisode(episodeId: string): Promise<ForgetEpisodeResponse> {
    this.requireNonEmpty(episodeId, 'episodeId');
    return this.http.request<ForgetEpisodeResponse>('DELETE', `/memory/${episodeId}`);
  }

  /**
   * Delete all memory episodes for a session.
   * @param sessionId Session identifier to purge.
   */
  async forgetSession(sessionId: string): Promise<ForgetSessionResponse> {
    this.requireNonEmpty(sessionId, 'sessionId');
    return this.http.request<ForgetSessionResponse>('DELETE', `/memory/session/${sessionId}`);
  }

  /**
   * Delete all memories and sessions for a user.
   * @param userId User identifier to purge.
   */
  async forgetUser(userId: string): Promise<ForgetUserResponse> {
    this.requireNonEmpty(userId, 'userId');
    return this.http.request<ForgetUserResponse>('DELETE', `/memory/user/${userId}`);
  }

  private getApiKeyFromEnv(): string | undefined {
    const processValue = (globalThis as { process?: { env?: Record<string, string | undefined> } }).process;
    return processValue?.env?.REMEMBR_API_KEY;
  }

  private requireNonEmpty(value: string, paramName: string): void {
    if (!value || !value.trim()) {
      throw new Error(`${paramName} is required and must be a non-empty string`);
    }
  }

  private validatePagination(limit: number, offset: number): void {
    if (limit < 1) {
      throw new Error('limit must be greater than 0');
    }
    if (offset < 0) {
      throw new Error('offset must be greater than or equal to 0');
    }
  }
}
