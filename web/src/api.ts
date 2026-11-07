import { t } from './i18n.js';
import type {
  ApiError,
  Appeal,
  AppealCreate,
  AppealQueueItem,
  BatchRequest,
  Checklist,
  ChecklistSummary,
  ConversationSummary,
  DecisionCreate,
  DecisionResult,
  EvaluationSummary,
  EvaluationView,
  GroupAnalytics,
  Job,
  DialogFacts,
  RawCall,
  Record as DialogRecord,
} from './types.gen.js';

/** Ответ GET /api/profiles (не входит в сгенерированные контракты). */
export interface ProfileInfo {
  name: string;
  model: string;
  provider: string;
}

/** Ошибка API: message = ApiError.error, details — построчные причины. */
export class ApiFail extends Error {
  constructor(
    readonly status: number,
    message: string,
    readonly details: string[] | null = null,
  ) {
    super(message);
    this.name = 'ApiFail';
  }
}

const sleep = (ms: number, signal?: AbortSignal) =>
  new Promise<void>((resolve) => {
    const timer = setTimeout(resolve, ms);
    signal?.addEventListener('abort', () => {
      clearTimeout(timer);
      resolve();
    });
  });

export class Api {
  constructor(private readonly base: string) {}

  private async request<T>(method: string, path: string, body?: unknown): Promise<T> {
    let res: Response;
    try {
      res = await fetch(this.base + path, {
        method,
        headers: body === undefined ? undefined : { 'Content-Type': 'application/json' },
        body: body === undefined ? undefined : JSON.stringify(body),
      });
    } catch {
      throw new ApiFail(0, t.common.networkError);
    }
    if (!res.ok) {
      let err: Partial<ApiError> = {};
      try {
        err = (await res.json()) as Partial<ApiError>;
      } catch {
        /* тело не JSON */
      }
      throw new ApiFail(res.status, err.error || `${t.common.error} ${res.status}`, err.details ?? null);
    }
    return (await res.json()) as T;
  }

  profiles(): Promise<ProfileInfo[]> {
    return this.request('GET', '/profiles');
  }
  conversations(group: string, refresh = false): Promise<ConversationSummary[]> {
    const q = refresh ? '?refresh=true' : '';
    return this.request('GET', `/datasets/${encodeURIComponent(group)}/conversations${q}`);
  }
  analytics(group: string): Promise<GroupAnalytics> {
    return this.request('GET', `/datasets/${encodeURIComponent(group)}/analytics`);
  }
  record(group: string, cid: string): Promise<DialogRecord> {
    return this.request('GET', `/datasets/${encodeURIComponent(group)}/conversations/${encodeURIComponent(cid)}`);
  }
  facts(group: string, cid: string): Promise<DialogFacts> {
    return this.request('GET', `/datasets/${encodeURIComponent(group)}/conversations/${encodeURIComponent(cid)}/facts`);
  }
  checklists(): Promise<ChecklistSummary[]> {
    return this.request('GET', '/checklists');
  }
  checklist(id: string, version?: number): Promise<Checklist> {
    const q = version === undefined ? '' : `?version=${version}`;
    return this.request('GET', `/checklists/${encodeURIComponent(id)}${q}`);
  }
  createChecklist(c: Checklist): Promise<Checklist> {
    return this.request('POST', '/checklists', c);
  }
  updateChecklist(c: Checklist): Promise<Checklist> {
    return this.request('PUT', `/checklists/${encodeURIComponent(c.id)}`, c);
  }
  batch(req: BatchRequest): Promise<Job> {
    return this.request('POST', '/evaluations/batch', req);
  }
  job(id: string): Promise<Job> {
    return this.request('GET', `/jobs/${encodeURIComponent(id)}`);
  }
  evaluationsFor(cid: string): Promise<EvaluationSummary[]> {
    return this.request('GET', `/conversations/${encodeURIComponent(cid)}/evaluations`);
  }
  evaluation(id: string): Promise<EvaluationView> {
    return this.request('GET', `/evaluations/${encodeURIComponent(id)}`);
  }
  raw(id: string): Promise<RawCall[]> {
    return this.request('GET', `/evaluations/${encodeURIComponent(id)}/raw`);
  }
  createAppeal(body: AppealCreate): Promise<Appeal> {
    return this.request('POST', '/appeals', body);
  }
  appeals(status?: 'open' | 'resolved'): Promise<AppealQueueItem[]> {
    const q = status ? `?status=${status}` : '';
    return this.request('GET', `/appeals${q}`);
  }
  decide(id: string, body: DecisionCreate): Promise<DecisionResult> {
    return this.request('POST', `/appeals/${encodeURIComponent(id)}/decision`, body);
  }

  /** Запускает пакет и опрашивает /jobs/{id} раз в секунду, пока state != finished. */
  async runBatch(req: BatchRequest, onProgress: (job: Job) => void, signal?: AbortSignal): Promise<Job> {
    let job = await this.batch(req);
    onProgress(job);
    while (job.state !== 'finished' && !signal?.aborted) {
      await sleep(1000, signal);
      if (signal?.aborted) break;
      job = await this.job(job.id);
      onProgress(job);
    }
    return job;
  }
}
