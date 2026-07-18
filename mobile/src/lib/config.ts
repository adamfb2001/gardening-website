import Constants from 'expo-constants';
import { Platform } from 'react-native';

/**
 * Best-guess backend URL when the user hasn't set one: the machine running
 * Metro (which served this JS to Expo Go) is normally also running the
 * backend, so reuse its host with the backend port. Overridable in Settings —
 * required when using `expo start --tunnel`, where the bundle host is a
 * tunnel domain that doesn't serve the API.
 */
export const BACKEND_PORT = 8000;

export function guessDefaultBaseUrl(): string {
  const hostUri: string | undefined =
    Constants.expoConfig?.hostUri ?? (Constants as any).expoGoConfig?.debuggerHost;
  const host = hostUri?.split(':')[0];
  if (host && !host.endsWith('.exp.direct')) {
    return `http://${host}:${BACKEND_PORT}`;
  }
  if (Platform.OS === 'web' && typeof window !== 'undefined' && window.location?.hostname) {
    return `http://${window.location.hostname}:${BACKEND_PORT}`;
  }
  return `http://localhost:${BACKEND_PORT}`;
}

export function uuid4(): string {
  const cryptoObj: any = (globalThis as any).crypto;
  if (cryptoObj?.randomUUID) return cryptoObj.randomUUID();
  const bytes = new Uint8Array(16);
  if (cryptoObj?.getRandomValues) {
    cryptoObj.getRandomValues(bytes);
  } else {
    for (let i = 0; i < 16; i += 1) bytes[i] = Math.floor(Math.random() * 256);
  }
  bytes[6] = (bytes[6] & 0x0f) | 0x40;
  bytes[8] = (bytes[8] & 0x3f) | 0x80;
  const hex = Array.from(bytes, (b) => b.toString(16).padStart(2, '0'));
  return `${hex.slice(0, 4).join('')}-${hex.slice(4, 6).join('')}-${hex.slice(6, 8).join('')}-${hex.slice(8, 10).join('')}-${hex.slice(10).join('')}`;
}
