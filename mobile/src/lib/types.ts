/** Mirrors the backend contract: note schema (§4.4) and job shapes (§6). */

export type PlatformId = 'youtube_shorts' | 'tiktok' | 'instagram_reels' | 'facebook_reels';

export type JobStatus =
  | 'queued'
  | 'resolving'
  | 'transcribing'
  | 'analysing'
  | 'synthesising'
  | 'complete'
  | 'failed';

export const TERMINAL_STATUSES: JobStatus[] = ['complete', 'failed'];

export interface Step {
  n: number;
  text: string;
}

export interface Quote {
  text: string;
  timestamp_s: number;
}

export interface Entities {
  people: string[];
  products: string[];
  places: string[];
  tools: string[];
  links_mentioned: string[];
}

export interface Confidence {
  audio: number;
  visual: number;
  overall: number;
}

export interface NoteData {
  title: string;
  summary: string;
  key_points: string[];
  steps: Step[];
  entities: Entities;
  quotes: Quote[];
  category: string;
  tags: string[];
  confidence: Confidence;
  caveats: string[];
  transcript?: string | null;
  creator_handle?: string | null;
  video_title?: string | null;
}

export interface JobError {
  code: string;
  message: string;
  retryable: boolean;
}

export interface JobView {
  job_id: string;
  status: JobStatus;
  progress: number;
  note: NoteData | null;
  error: JobError | null;
  url: string;
  created_at: string;
  updated_at: string;
}

export interface JobCreateResponse {
  job_id: string;
  status: JobStatus;
  dedup_of: string | null;
}

export interface DeviceRegistration {
  device_id: string;
  token: string;
  expires_at: string;
}

/** A completed note as stored on this device (the phone is the source of
 * truth for the library; the backend only processes). */
export interface StoredNote {
  id: string; // backend job_id at creation time
  sourceUrl: string;
  platform: PlatformId | null;
  note: NoteData;
  createdAt: string;
  favourite: boolean;
}

/** An in-flight or failed ingest being tracked against the backend. */
export interface TrackedJob {
  jobId: string;
  clientId: string;
  url: string;
  status: JobStatus;
  progress: number;
  error: JobError | null;
  createdAt: string;
  /** Set when the backend no longer knows the job (e.g. it restarted). */
  lost?: boolean;
}

const PLATFORM_LABELS: Record<PlatformId, string> = {
  youtube_shorts: 'YouTube Shorts',
  tiktok: 'TikTok',
  instagram_reels: 'Instagram Reels',
  facebook_reels: 'Facebook Reels',
};

export function platformLabel(platform: PlatformId | null): string {
  return platform ? PLATFORM_LABELS[platform] : 'Link';
}

/** Client-side twin of the backend's host → platform mapping (badges only —
 * the backend remains the authority on support). */
export function detectPlatform(url: string): PlatformId | null {
  let host: string;
  try {
    host = new URL(url).hostname.toLowerCase();
  } catch {
    return null;
  }
  host = host.replace(/^(www\.|m\.|web\.)/, '');
  if (host === 'youtube.com' || host === 'youtu.be' || host.endsWith('.youtube.com')) {
    return 'youtube_shorts';
  }
  if (host === 'tiktok.com' || host.endsWith('.tiktok.com')) return 'tiktok';
  if (host === 'instagram.com' || host.endsWith('.instagram.com')) return 'instagram_reels';
  if (host === 'facebook.com' || host === 'fb.com' || host === 'fb.watch' || host.endsWith('.facebook.com')) {
    return 'facebook_reels';
  }
  return null;
}

export function looksLikeHttpUrl(text: string): boolean {
  try {
    const parsed = new URL(text.trim());
    return (parsed.protocol === 'http:' || parsed.protocol === 'https:') && !!parsed.hostname;
  } catch {
    return false;
  }
}

/** Pull the first http(s) URL out of shared text (some apps share prose
 * containing the link). */
export function extractUrl(text: string): string | null {
  const match = text.match(/https?:\/\/[^\s"'<>]+/);
  return match ? match[0] : null;
}
