import AsyncStorage from '@react-native-async-storage/async-storage';
import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import { AppState } from 'react-native';

import * as api from './api';
import { ApiError } from './api';
import { guessDefaultBaseUrl, uuid4 } from './config';
import {
  TERMINAL_STATUSES,
  type StoredNote,
  type TrackedJob,
  detectPlatform,
  extractUrl,
  looksLikeHttpUrl,
} from './types';

const KEYS = {
  notes: 'clipnotes.notes.v1',
  jobs: 'clipnotes.jobs.v1',
  device: 'clipnotes.device.v1',
  baseUrl: 'clipnotes.baseurl.v1',
};

const POLL_INTERVAL_MS = 2000;

interface DeviceIdentity {
  baseUrl: string;
  deviceId: string;
  token: string;
}

export type SubmitResult =
  | { kind: 'queued' }
  | { kind: 'duplicate'; noteId: string }
  | { kind: 'invalid' };

interface ClipNotesState {
  ready: boolean;
  notes: StoredNote[];
  jobs: TrackedJob[];
  baseUrl: string;
  baseUrlOverride: string | null;
  deviceId: string | null;
  submitUrl: (text: string) => Promise<SubmitResult>;
  retryTrackedJob: (jobId: string) => Promise<void>;
  dismissJob: (jobId: string) => void;
  deleteNote: (noteId: string) => void;
  toggleFavourite: (noteId: string) => void;
  clearAllNotes: () => void;
  setBaseUrlOverride: (url: string | null) => Promise<void>;
  refreshNow: () => void;
}

const Ctx = createContext<ClipNotesState | null>(null);

function deviceLocale(): string {
  try {
    return Intl.DateTimeFormat().resolvedOptions().locale || 'en';
  } catch {
    return 'en';
  }
}

export function ClipNotesProvider({ children }: { children: React.ReactNode }) {
  const [ready, setReady] = useState(false);
  const [notes, setNotes] = useState<StoredNote[]>([]);
  const [jobs, setJobs] = useState<TrackedJob[]>([]);
  const [baseUrlOverride, setOverride] = useState<string | null>(null);
  const [deviceId, setDeviceId] = useState<string | null>(null);

  const baseUrl = baseUrlOverride ?? guessDefaultBaseUrl();
  const deviceRef = useRef<DeviceIdentity | null>(null);
  const pollingRef = useRef(false);
  // Refs mirror state the poll loop reads, so the interval closure stays fresh.
  const jobsRef = useRef<TrackedJob[]>([]);
  jobsRef.current = jobs;
  const baseUrlRef = useRef(baseUrl);
  baseUrlRef.current = baseUrl;

  // ---- boot: load persisted state -----------------------------------------
  useEffect(() => {
    (async () => {
      try {
        const [rawNotes, rawJobs, rawDevice, rawBase] = await Promise.all([
          AsyncStorage.getItem(KEYS.notes),
          AsyncStorage.getItem(KEYS.jobs),
          AsyncStorage.getItem(KEYS.device),
          AsyncStorage.getItem(KEYS.baseUrl),
        ]);
        if (rawNotes) setNotes(JSON.parse(rawNotes));
        if (rawJobs) setJobs(JSON.parse(rawJobs));
        if (rawDevice) {
          deviceRef.current = JSON.parse(rawDevice);
          setDeviceId(deviceRef.current?.deviceId ?? null);
        }
        if (rawBase) setOverride(JSON.parse(rawBase));
      } catch {
        // Corrupt local state: start empty rather than crash.
      } finally {
        setReady(true);
      }
    })();
  }, []);

  // ---- persistence --------------------------------------------------------
  useEffect(() => {
    if (ready) AsyncStorage.setItem(KEYS.notes, JSON.stringify(notes)).catch(() => {});
  }, [notes, ready]);
  useEffect(() => {
    if (ready) AsyncStorage.setItem(KEYS.jobs, JSON.stringify(jobs)).catch(() => {});
  }, [jobs, ready]);

  // ---- device identity ----------------------------------------------------
  const getToken = useCallback(async (): Promise<string> => {
    const current = deviceRef.current;
    if (current && current.baseUrl === baseUrlRef.current) return current.token;
    const registration = await api.registerDevice(baseUrlRef.current);
    const identity: DeviceIdentity = {
      baseUrl: baseUrlRef.current,
      deviceId: registration.device_id,
      token: registration.token,
    };
    deviceRef.current = identity;
    setDeviceId(identity.deviceId);
    AsyncStorage.setItem(KEYS.device, JSON.stringify(identity)).catch(() => {});
    return identity.token;
  }, []);

  /** Run an authed call; if the token is stale (server restarted with a new
   * secret, base URL changed), re-register once and retry. */
  const withAuth = useCallback(
    async <T,>(fn: (token: string) => Promise<T>): Promise<T> => {
      const token = await getToken();
      try {
        return await fn(token);
      } catch (error) {
        if (error instanceof ApiError && error.status === 401) {
          deviceRef.current = null;
          return fn(await getToken());
        }
        throw error;
      }
    },
    [getToken],
  );

  // ---- polling ------------------------------------------------------------
  const tick = useCallback(async () => {
    if (pollingRef.current) return;
    const active = jobsRef.current.filter(
      (job) => !TERMINAL_STATUSES.includes(job.status) && !job.lost,
    );
    if (active.length === 0) return;
    pollingRef.current = true;
    try {
      for (const job of active) {
        try {
          const view = await withAuth((token) => api.getJob(baseUrlRef.current, token, job.jobId));
          if (view.status === 'complete' && view.note) {
            const note: StoredNote = {
              id: view.job_id,
              sourceUrl: job.url,
              platform: detectPlatform(job.url),
              note: view.note,
              createdAt: new Date().toISOString(),
              favourite: false,
            };
            setNotes((prev) => (prev.some((n) => n.id === note.id) ? prev : [note, ...prev]));
            setJobs((prev) => prev.filter((j) => j.jobId !== job.jobId));
          } else {
            setJobs((prev) =>
              prev.map((j) =>
                j.jobId === job.jobId
                  ? { ...j, status: view.status, progress: view.progress, error: view.error }
                  : j,
              ),
            );
          }
        } catch (error) {
          if (error instanceof ApiError && error.status === 404) {
            // The backend forgot this job (in-memory store + restart).
            setJobs((prev) =>
              prev.map((j) =>
                j.jobId === job.jobId
                  ? {
                      ...j,
                      lost: true,
                      status: 'failed',
                      error: {
                        code: 'lost',
                        message: 'The server no longer knows this job (it may have restarted). Retry to resubmit.',
                        retryable: true,
                      },
                    }
                  : j,
              ),
            );
          }
          // Network blips: leave the job as-is and try again next tick.
        }
      }
    } finally {
      pollingRef.current = false;
    }
  }, [withAuth]);

  const hasActiveJobs = jobs.some((job) => !TERMINAL_STATUSES.includes(job.status) && !job.lost);

  useEffect(() => {
    if (!ready || !hasActiveJobs) return;
    tick();
    const interval = setInterval(tick, POLL_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [ready, hasActiveJobs, tick]);

  useEffect(() => {
    const subscription = AppState.addEventListener('change', (state) => {
      if (state === 'active') tick();
    });
    return () => subscription.remove();
  }, [tick]);

  // ---- actions ------------------------------------------------------------
  const submitUrl = useCallback(
    async (text: string): Promise<SubmitResult> => {
      const url = extractUrl(text) ?? text.trim();
      if (!looksLikeHttpUrl(url)) return { kind: 'invalid' };

      const clientId = uuid4();
      const response = await withAuth((token) =>
        api.createJob(baseUrlRef.current, token, {
          client_id: clientId,
          url,
          locale: deviceLocale(),
        }),
      );

      if (response.dedup_of) {
        const existing = notes.find((n) => n.id === response.dedup_of);
        if (existing) {
          // Already in the library — drop the redundant server job.
          withAuth((token) => api.deleteJob(baseUrlRef.current, token, response.job_id)).catch(
            () => {},
          );
          return { kind: 'duplicate', noteId: existing.id };
        }
      }

      setJobs((prev) =>
        prev.some((j) => j.jobId === response.job_id)
          ? prev
          : [
              {
                jobId: response.job_id,
                clientId,
                url,
                status: response.status,
                progress: 0,
                error: null,
                createdAt: new Date().toISOString(),
              },
              ...prev,
            ],
      );
      return { kind: 'queued' };
    },
    [notes, withAuth],
  );

  const retryTrackedJob = useCallback(
    async (jobId: string) => {
      const job = jobsRef.current.find((j) => j.jobId === jobId);
      if (!job) return;
      const resubmit = async () => {
        const response = await withAuth((token) =>
          api.createJob(baseUrlRef.current, token, {
            client_id: job.clientId,
            url: job.url,
            locale: deviceLocale(),
          }),
        );
        setJobs((prev) =>
          prev.map((j) =>
            j.jobId === jobId
              ? {
                  ...j,
                  jobId: response.job_id,
                  status: response.status,
                  progress: 0,
                  error: null,
                  lost: false,
                }
              : j,
          ),
        );
      };

      if (job.lost) {
        await resubmit();
        return;
      }
      try {
        const view = await withAuth((token) => api.retryJob(baseUrlRef.current, token, jobId));
        setJobs((prev) =>
          prev.map((j) =>
            j.jobId === jobId
              ? { ...j, status: view.status, progress: view.progress, error: view.error }
              : j,
          ),
        );
      } catch (error) {
        if (error instanceof ApiError && error.status === 404) {
          await resubmit();
        } else {
          throw error;
        }
      }
    },
    [withAuth],
  );

  const dismissJob = useCallback(
    (jobId: string) => {
      setJobs((prev) => prev.filter((j) => j.jobId !== jobId));
      withAuth((token) => api.deleteJob(baseUrlRef.current, token, jobId)).catch(() => {});
    },
    [withAuth],
  );

  const deleteNote = useCallback((noteId: string) => {
    setNotes((prev) => prev.filter((n) => n.id !== noteId));
  }, []);

  const toggleFavourite = useCallback((noteId: string) => {
    setNotes((prev) =>
      prev.map((n) => (n.id === noteId ? { ...n, favourite: !n.favourite } : n)),
    );
  }, []);

  const clearAllNotes = useCallback(() => setNotes([]), []);

  const setBaseUrlOverride = useCallback(async (url: string | null) => {
    const trimmed = url?.trim().replace(/\/+$/, '') || null;
    setOverride(trimmed);
    // A different backend means a different signing key — force re-registration.
    deviceRef.current = null;
    await AsyncStorage.setItem(KEYS.baseUrl, JSON.stringify(trimmed));
  }, []);

  const value = useMemo<ClipNotesState>(
    () => ({
      ready,
      notes,
      jobs,
      baseUrl,
      baseUrlOverride,
      deviceId,
      submitUrl,
      retryTrackedJob,
      dismissJob,
      deleteNote,
      toggleFavourite,
      clearAllNotes,
      setBaseUrlOverride,
      refreshNow: tick,
    }),
    [
      ready,
      notes,
      jobs,
      baseUrl,
      baseUrlOverride,
      deviceId,
      submitUrl,
      retryTrackedJob,
      dismissJob,
      deleteNote,
      toggleFavourite,
      clearAllNotes,
      setBaseUrlOverride,
      tick,
    ],
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useClipNotes(): ClipNotesState {
  const state = useContext(Ctx);
  if (!state) throw new Error('useClipNotes must be used inside ClipNotesProvider');
  return state;
}
