import React from 'react';
import { ActivityIndicator, StyleSheet, View } from 'react-native';

import { Button, ProgressBar } from '@/components/bits';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { Spacing } from '@/constants/theme';
import type { JobStatus, TrackedJob } from '@/lib/types';

const STATUS_LABELS: Record<JobStatus, string> = {
  queued: 'Queued…',
  resolving: 'Fetching video info…',
  transcribing: 'Transcribing audio…',
  analysing: 'Reading visuals…',
  synthesising: 'Writing your note…',
  complete: 'Done',
  failed: 'Failed',
};

export function JobCard({
  job,
  onRetry,
  onDismiss,
}: {
  job: TrackedJob;
  onRetry: () => void;
  onDismiss: () => void;
}) {
  const failed = job.status === 'failed';
  return (
    <ThemedView type="backgroundElement" style={styles.card}>
      <View style={styles.statusRow}>
        {!failed && <ActivityIndicator size="small" />}
        <ThemedText type="smallBold" style={failed ? styles.failedText : undefined}>
          {STATUS_LABELS[job.status]}
        </ThemedText>
      </View>
      <ThemedText type="small" themeColor="textSecondary" numberOfLines={1}>
        {job.url}
      </ThemedText>
      {!failed && <ProgressBar progress={job.progress} />}
      {failed && (
        <>
          <ThemedText type="small" style={styles.failedText}>
            {job.error?.message ?? 'Something went wrong.'}
          </ThemedText>
          <View style={styles.actions}>
            {(job.error?.retryable ?? true) && (
              <Button label="Retry" onPress={onRetry} kind="secondary" />
            )}
            <Button label="Dismiss" onPress={onDismiss} kind="secondary" />
          </View>
        </>
      )}
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  card: {
    borderRadius: Spacing.three,
    padding: Spacing.three,
    gap: Spacing.two,
  },
  statusRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.two,
  },
  failedText: {
    color: '#D64545',
  },
  actions: {
    flexDirection: 'row',
    gap: Spacing.two,
  },
});
