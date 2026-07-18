import React, { useState } from 'react';
import { ScrollView, StyleSheet, TextInput, View } from 'react-native';

import { Button } from '@/components/bits';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { MaxContentWidth, Spacing } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';
import { health } from '@/lib/api';
import { guessDefaultBaseUrl } from '@/lib/config';
import { confirmAsync } from '@/lib/confirm';
import { useClipNotes } from '@/lib/store';

export default function SettingsScreen() {
  const theme = useTheme();
  const { baseUrl, baseUrlOverride, setBaseUrlOverride, deviceId, notes, clearAllNotes } =
    useClipNotes();
  const [draft, setDraft] = useState(baseUrlOverride ?? '');
  const [statusLine, setStatusLine] = useState<string | null>(null);

  const testConnection = async (url: string) => {
    setStatusLine('Checking…');
    try {
      const result = await health(url);
      setStatusLine(`Connected ✓ — backend v${result.version}`);
    } catch (error) {
      setStatusLine(error instanceof Error ? error.message : 'Could not connect.');
    }
  };

  const save = async () => {
    await setBaseUrlOverride(draft || null);
    const effective = draft.trim() ? draft.trim().replace(/\/+$/, '') : guessDefaultBaseUrl();
    await testConnection(effective);
  };

  const handleClear = async () => {
    const confirmed = await confirmAsync(
      'Delete all notes?',
      `This removes all ${notes.length} notes from this device. There is no undo.`,
      'Delete all',
    );
    if (confirmed) clearAllNotes();
  };

  return (
    <ThemedView style={styles.container}>
      <ScrollView contentContainerStyle={styles.content}>
        <View style={styles.section}>
          <ThemedText type="subtitle">Backend</ThemedText>
          <ThemedText type="small" themeColor="textSecondary">
            Where ClipNotes sends links for processing. Leave empty to use the machine serving
            this app via Expo (currently {guessDefaultBaseUrl()}).
          </ThemedText>
          <TextInput
            style={[styles.input, { backgroundColor: theme.backgroundElement, color: theme.text }]}
            placeholder={guessDefaultBaseUrl()}
            placeholderTextColor={theme.textSecondary}
            value={draft}
            onChangeText={setDraft}
            autoCapitalize="none"
            autoCorrect={false}
            inputMode="url"
            testID="baseurl-input"
          />
          <View style={styles.buttonRow}>
            <Button label="Save" onPress={save} />
            <Button label="Test connection" kind="secondary" onPress={() => testConnection(baseUrl)} />
          </View>
          {statusLine && <ThemedText type="small">{statusLine}</ThemedText>}
          <ThemedText type="small" themeColor="textSecondary">
            Active: {baseUrl}
            {deviceId ? `\nDevice: ${deviceId.slice(0, 12)}…` : ''}
          </ThemedText>
        </View>

        <View style={styles.section}>
          <ThemedText type="subtitle">Your data</ThemedText>
          <ThemedText type="small" themeColor="textSecondary">
            {notes.length} notes stored on this device. Notes are readable and searchable
            offline; only new ingests need the backend.
          </ThemedText>
          <Button label="Delete all notes" kind="danger" onPress={handleClear} />
        </View>

        <View style={styles.section}>
          <ThemedText type="subtitle">About</ThemedText>
          <ThemedText type="small" themeColor="textSecondary">
            ClipNotes turns short-form videos into searchable notes. Notes are private to this
            device, always keep a link back to the original creator, and are honest about
            uncertainty — the backend pipeline is currently stubbed (M1), so notes contain
            clearly-labelled placeholder content until real transcription lands (M2).
          </ThemedText>
          <ThemedText type="small" themeColor="textSecondary">
            Testing tip: any YouTube/TikTok/Instagram/Facebook link works. Add
            “stub-unavailable”, “stub-private”, “stub-toolong”, “stub-nospeech” or
            “stub-crash” to the link path to preview failure and edge states.
          </ThemedText>
        </View>
      </ScrollView>
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  content: {
    padding: Spacing.three,
    gap: Spacing.five,
    maxWidth: MaxContentWidth,
    alignSelf: 'center',
    width: '100%',
  },
  section: {
    gap: Spacing.two,
  },
  input: {
    borderRadius: Spacing.two,
    paddingHorizontal: Spacing.three,
    paddingVertical: Spacing.two + Spacing.half,
    fontSize: 15,
    minHeight: 40,
  },
  buttonRow: {
    flexDirection: 'row',
    gap: Spacing.two,
  },
});
