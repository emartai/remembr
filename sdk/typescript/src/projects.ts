import { RemembrHttp } from './http';

export interface ProjectMemory {
  id: string;
  space_id: string;
  content: string;
  author_id: string;
  author_kind: string;
  source_ref: string | null;
  run_id: string | null;
  state: 'active' | 'superseded' | 'expired' | 'deleted';
  supersedes_id: string | null;
  embedding_status: 'pending' | 'ready' | 'failed';
  embedding_error: string | null;
  created_at: string;
  expires_at: string | null;
}

export interface ProjectStore {
  content: string;
  idempotency_key: string;
  source_ref?: string;
  run_id?: string;
  supersedes_id?: string;
  expires_at?: string;
}

export interface ProjectSearch {
  query?: string;
  mode?: 'keyword' | 'semantic' | 'hybrid';
  limit?: number;
  offset?: number;
  context_chars?: number;
  include_inactive?: boolean;
}

export interface ProjectSearchResult {
  results: Array<ProjectMemory & { score: number; retrieval_reason: string; content_truncated: boolean }>;
  mode: string;
  space_id: string;
  offset: number;
  has_more: boolean;
  next_offset?: number | null;
  truncated: boolean;
  context_chars_used: number;
  score_explanation: string;
}

export class ProjectMemoryAPI {
  constructor(private readonly http: RemembrHttp) {}

  private path(space: string, memory?: string): string {
    const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
    if (!uuid.test(space) || (memory !== undefined && !uuid.test(memory))) {
      throw new Error('space and memory IDs must be UUIDs');
    }
    return `/projects/spaces/${space}` + (memory ? `/memories/${memory}` : '');
  }

  store(space: string, body: ProjectStore): Promise<ProjectMemory> {
    return this.http.request('POST', this.path(space) + '/memories', { body: { ...body } });
  }

  search(space: string, body: ProjectSearch = {}): Promise<ProjectSearchResult> {
    return this.http.request('POST', this.path(space) + '/search', { body: { ...body } });
  }

  get(space: string, memory: string): Promise<ProjectMemory> {
    return this.http.request('GET', this.path(space, memory));
  }

  status(space: string, memory: string): Promise<Pick<ProjectMemory, 'id' | 'state' | 'embedding_status' | 'embedding_error'>> {
    return this.http.request('GET', this.path(space, memory) + '/status');
  }

  delete(space: string, memory: string): Promise<{ deleted: boolean; id: string }> {
    return this.http.request('DELETE', this.path(space, memory));
  }
}
