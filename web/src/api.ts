import { t } from './i18n.js';
import type {
  ApiError,
  AsrProviderInfo,
  Attention,
  Confirmation,
  ConfirmationCreate,
  ConfirmationStats,
  Appeal,
  AppealCreate,
  AppealQueueItem,
  BatchRequest,
  Checklist,
  ChecklistSummary,
  ConversationSummary,
  DatasetStatus,
  CustomTranscriptRequest,
  DecisionCreate,
  DecisionResult,
  EvaluationSummary,
  EvaluationView,
  GroupAnalytics,
  Job,
  DialogFacts,
  RawCall,
  Record as DialogRecord,
  TranscribeRequest,
  TranscriptSourceInfo,
  UploadChatRequest,
} from './types.gen.js';

/** Язык загружаемого звонка: auto — определяет модель распознавания. */
export type UploadLanguage = 'auto' | 'RU' | 'KZ' | 'EN';
/** Ответ GET /api/criterion-reliability. */
export interface CriterionReliability {
  source: string | null;
  threshold?: number;
  criteria: { [criterionId: string]: { agree: number; n: number } };
}

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

  /** fetch + единый разбор ошибки (ApiError → ApiFail). Прерывание по `signal` пробрасывается как AbortError. */
  private async send(path: string, init: RequestInit = {}): Promise<Response> {
    let res: Response;
    try {
      res = await fetch(this.base + path, init);
    } catch (e) {
      if (init.signal?.aborted) throw e;
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
    return res;
  }

  private async request<T>(method: string, path: string, body?: unknown): Promise<T> {
    const res = await this.send(path, {
      method,
      headers: body === undefined ? undefined : { 'Content-Type': 'application/json' },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    return (await res.json()) as T;
  }

  profiles(): Promise<ProfileInfo[]> {
    return this.request('GET', '/profiles');
  }
  conversations(group: string, refresh = false): Promise<ConversationSummary[]> {
    const q = refresh ? '?refresh=true' : '';
    return this.request('GET', `/datasets/${encodeURIComponent(group)}/conversations${q}`);
  }
  /** Фоновая загрузка группы из API организаторов (запускается `conversations(group, true)`). */
  datasetStatus(group: string): Promise<DatasetStatus> {
    return this.request('GET', `/datasets/${encodeURIComponent(group)}/status`);
  }
  /** `baseline` — группа, с которой сравнивать распределение (дрейф); без неё сравниваются половины группы. */
  analytics(group: string, baseline?: string): Promise<GroupAnalytics> {
    const q = baseline ? `?baseline=${encodeURIComponent(baseline)}` : '';
    return this.request('GET', `/datasets/${encodeURIComponent(group)}/analytics${q}`);
  }
  /** `source` — источник транскрипта (api — организатора, по умолчанию). */
  record(group: string, cid: string, source?: string): Promise<DialogRecord> {
    const q = source ? `?source=${encodeURIComponent(source)}` : '';
    return this.request('GET', `/datasets/${encodeURIComponent(group)}/conversations/${encodeURIComponent(cid)}${q}`);
  }
  facts(group: string, cid: string, source?: string): Promise<DialogFacts> {
    const q = source ? `?source=${encodeURIComponent(source)}` : '';
    return this.request('GET', `/datasets/${encodeURIComponent(group)}/conversations/${encodeURIComponent(cid)}/facts${q}`);
  }
  transcripts(cid: string): Promise<TranscriptSourceInfo[]> {
    return this.request('GET', `/conversations/${encodeURIComponent(cid)}/transcripts`);
  }
  /** Распознаёт звонок провайдером (долго: аудио → ASR → роли и маскирование) и сохраняет транскрипт. */
  transcribe(cid: string, body: TranscribeRequest): Promise<DialogRecord> {
    return this.request('POST', `/conversations/${encodeURIComponent(cid)}/transcribe`, body);
  }
  putCustomTranscript(cid: string, body: CustomTranscriptRequest): Promise<DialogRecord> {
    return this.request('PUT', `/conversations/${encodeURIComponent(cid)}/transcripts/custom`, body);
  }
  /** Новый звонок в группе UPLOADS: файл → распознавание → роли и маскирование (долго, до пары минут). */
  async uploadCall(file: File, language: UploadLanguage, provider: string, signal?: AbortSignal): Promise<DialogRecord> {
    const form = new FormData();
    form.append('file', file, file.name);
    form.append('language', language);
    form.append('provider', provider);
    const res = await this.send('/uploads/call', { method: 'POST', body: form, signal });
    return (await res.json()) as DialogRecord;
  }
  asrProviders(): Promise<AsrProviderInfo[]> {
    return this.request('GET', '/asr/providers');
  }
  uploadChat(body: UploadChatRequest): Promise<DialogRecord> {
    return this.request('POST', '/uploads/chat', body);
  }
  async deleteUpload(cid: string): Promise<void> {
    await this.send(`/uploads/${encodeURIComponent(cid)}`, { method: 'DELETE' });
  }
  /** Коучинг «как было бы правильно»: правка реплик оператора, проверенная судьёй по одному критерию. */
  recourse<T>(evaluationId: string, criterionId: string): Promise<T> {
    return this.request('POST', `/evaluations/${encodeURIComponent(evaluationId)}/recourse`, { criterion_id: criterionId });
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
  /** ZIP «дела» по оценке (RegPack); ошибки — как у остальных запросов. */
  async regpack(group: string, cid: string, evaluationId: string): Promise<{ blob: Blob; name: string; selfcheckOk: boolean }> {
    const q = `?group_id=${encodeURIComponent(group)}&evaluation_id=${encodeURIComponent(evaluationId)}`;
    const res = await this.send(`/conversations/${encodeURIComponent(cid)}/regpack${q}`);
    const m = /filename="([^"]+)"/.exec(res.headers.get('Content-Disposition') ?? '');
    return { blob: await res.blob(), name: m?.[1] ?? `regpack-${cid}.zip`, selfcheckOk: res.headers.get('X-Regpack-Selfcheck') === 'ok' };
  }
  /** Измеренное согласие судьи с разметкой на DEV по критериям (data/criterion_reliability.json). */
  criterionReliability(): Promise<CriterionReliability> {
    return this.request('GET', '/criterion-reliability');
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
  attention(evaluationId: string): Promise<Attention> {
    return this.request('GET', `/evaluations/${encodeURIComponent(evaluationId)}/attention`);
  }
  confirmations(evaluationId: string): Promise<Confirmation[]> {
    return this.request('GET', `/evaluations/${encodeURIComponent(evaluationId)}/confirmations`);
  }
  createConfirmation(evaluationId: string, body: ConfirmationCreate): Promise<Confirmation> {
    return this.request('POST', `/evaluations/${encodeURIComponent(evaluationId)}/confirmations`, body);
  }
  confirmationStats(): Promise<ConfirmationStats> {
    return this.request('GET', '/confirmations/stats');
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
