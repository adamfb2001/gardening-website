import { useLocalSearchParams, useRouter } from 'expo-router';
import React, { useEffect, useRef, useState } from 'react';
import { ActivityIndicator, StyleSheet } from 'react-native';

import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { Spacing } from '@/constants/theme';
import { useClipNotes } from '@/lib/store';

/**
 * Deep-link ingest: opening
 *   exp://<metro-host>/--/ingest?url=<video link>   (Expo Go)
 * submits the link and lands in the library. Pair it with an iOS Shortcut in
 * the share sheet ("Open URL" on the shared link) to approximate the native
 * share extension until we have a dev build.
 */
export default function IngestScreen() {
  const { url } = useLocalSearchParams<{ url?: string }>();
  const router = useRouter();
  const { ready, submitUrl } = useClipNotes();
  const [message, setMessage] = useState('Saving to ClipNotes…');
  const startedRef = useRef(false);

  useEffect(() => {
    if (!ready || startedRef.current) return;
    startedRef.current = true;
    const shared = typeof url === 'string' ? url : null;
    (async () => {
      if (!shared) {
        router.replace('/');
        return;
      }
      try {
        await submitUrl(shared);
      } catch (error) {
        setMessage(error instanceof Error ? error.message : 'Something went wrong.');
        await new Promise((resolve) => setTimeout(resolve, 1500));
      }
      router.replace('/');
    })();
  }, [ready, url, router, submitUrl]);

  return (
    <ThemedView style={styles.container}>
      <ActivityIndicator />
      <ThemedText themeColor="textSecondary">{message}</ThemedText>
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    gap: Spacing.three,
  },
});
