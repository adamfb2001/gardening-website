import * as Clipboard from 'expo-clipboard';
import { Link } from 'expo-router';
import React, { useMemo, useRef, useState } from 'react';
import {
  FlatList,
  RefreshControl,
  ScrollView,
  StyleSheet,
  TextInput,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { ACCENT, Button, Chip } from '@/components/bits';
import { JobCard } from '@/components/job-card';
import { NoteCard } from '@/components/note-card';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { MaxContentWidth, Spacing } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';
import { useClipNotes } from '@/lib/store';
import { extractUrl, type StoredNote } from '@/lib/types';

const FAVOURITES = '★ Favourites';

function matchesQuery(stored: StoredNote, query: string): boolean {
  const haystack = [
    stored.note.title,
    stored.note.summary,
    ...stored.note.key_points,
    ...stored.note.tags,
    ...stored.note.steps.map((step) => step.text),
    ...stored.note.quotes.map((quote) => quote.text),
    stored.note.category,
    stored.sourceUrl,
  ]
    .join('\n')
    .toLowerCase();
  return query
    .toLowerCase()
    .split(/\s+/)
    .filter(Boolean)
    .every((term) => haystack.includes(term));
}

export default function LibraryScreen() {
  const theme = useTheme();
  const { ready, notes, jobs, submitUrl, retryTrackedJob, dismissJob, refreshNow } =
    useClipNotes();

  const [input, setInput] = useState('');
  const [query, setQuery] = useState('');
  const [categoryFilter, setCategoryFilter] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const messageTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const flash = (text: string) => {
    setMessage(text);
    if (messageTimer.current) clearTimeout(messageTimer.current);
    messageTimer.current = setTimeout(() => setMessage(null), 5000);
  };

  const handleSubmit = async (text: string) => {
    if (!text.trim()) return;
    try {
      const result = await submitUrl(text);
      if (result.kind === 'queued') {
        setInput('');
        flash('Saved — processing…');
      } else if (result.kind === 'duplicate') {
        setInput('');
        flash('Already in your library.');
      } else {
        flash("That doesn't look like a link.");
      }
    } catch (error) {
      flash(error instanceof Error ? error.message : 'Something went wrong.');
    }
  };

  const handlePaste = async () => {
    const text = await Clipboard.getStringAsync();
    const url = extractUrl(text);
    if (!url) {
      flash('No link found on the clipboard.');
      return;
    }
    setInput(url);
    await handleSubmit(url);
  };

  const categories = useMemo(() => {
    const seen = new Set(notes.map((n) => n.note.category));
    return [...seen].sort();
  }, [notes]);

  const filtered = useMemo(() => {
    return notes.filter((stored) => {
      if (categoryFilter === FAVOURITES && !stored.favourite) return false;
      if (categoryFilter && categoryFilter !== FAVOURITES && stored.note.category !== categoryFilter) {
        return false;
      }
      if (query.trim() && !matchesQuery(stored, query)) return false;
      return true;
    });
  }, [notes, query, categoryFilter]);

  const header = (
    <View style={styles.header}>
      <View style={styles.titleRow}>
        <ThemedText type="title">ClipNotes</ThemedText>
        <Link href="/settings">
          <ThemedText type="linkPrimary">Settings</ThemedText>
        </Link>
      </View>

      <View style={styles.ingestRow}>
        <TextInput
          style={[
            styles.input,
            { backgroundColor: theme.backgroundElement, color: theme.text },
          ]}
          placeholder="Paste a video link…"
          placeholderTextColor={theme.textSecondary}
          value={input}
          onChangeText={setInput}
          autoCapitalize="none"
          autoCorrect={false}
          inputMode="url"
          onSubmitEditing={() => handleSubmit(input)}
          testID="url-input"
        />
        <Button label="Save" onPress={() => handleSubmit(input)} />
      </View>
      <View style={styles.pasteRow}>
        <Button label="Paste link" onPress={handlePaste} kind="secondary" />
        {message && (
          <ThemedText type="small" style={{ color: ACCENT, flexShrink: 1 }}>
            {message}
          </ThemedText>
        )}
      </View>

      {jobs.length > 0 && (
        <View style={styles.tray}>
          <ThemedText type="smallBold" themeColor="textSecondary">
            PROCESSING
          </ThemedText>
          {jobs.map((job) => (
            <JobCard
              key={job.jobId}
              job={job}
              onRetry={() => retryTrackedJob(job.jobId).catch(() => {})}
              onDismiss={() => dismissJob(job.jobId)}
            />
          ))}
        </View>
      )}

      <TextInput
        style={[
          styles.input,
          { backgroundColor: theme.backgroundElement, color: theme.text },
        ]}
        placeholder="Search your notes…"
        placeholderTextColor={theme.textSecondary}
        value={query}
        onChangeText={setQuery}
        autoCapitalize="none"
        testID="search-input"
      />

      {notes.length > 0 && (
        <ScrollView horizontal showsHorizontalScrollIndicator={false}>
          <View style={styles.chipRow}>
            <Chip
              label="All"
              active={categoryFilter === null}
              onPress={() => setCategoryFilter(null)}
            />
            <Chip
              label={FAVOURITES}
              active={categoryFilter === FAVOURITES}
              onPress={() => setCategoryFilter(FAVOURITES)}
            />
            {categories.map((category) => (
              <Chip
                key={category}
                label={category}
                active={categoryFilter === category}
                onPress={() => setCategoryFilter(category)}
              />
            ))}
          </View>
        </ScrollView>
      )}
    </View>
  );

  return (
    <ThemedView style={styles.container}>
      <SafeAreaView style={styles.safeArea} edges={['top', 'left', 'right']}>
        <FlatList
          data={ready ? filtered : []}
          keyExtractor={(item) => item.id}
          renderItem={({ item }) => <NoteCard note={item} />}
          ListHeaderComponent={header}
          ListEmptyComponent={
            ready ? (
              <ThemedText themeColor="textSecondary" style={styles.empty}>
                {notes.length === 0
                  ? 'No notes yet. Paste a link to a YouTube Short, TikTok, or Reel above to get started.'
                  : 'No notes match your search.'}
              </ThemedText>
            ) : null
          }
          contentContainerStyle={styles.listContent}
          keyboardShouldPersistTaps="handled"
          refreshControl={
            <RefreshControl
              refreshing={refreshing}
              onRefresh={() => {
                setRefreshing(true);
                refreshNow();
                setTimeout(() => setRefreshing(false), 600);
              }}
            />
          }
        />
      </SafeAreaView>
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    flexDirection: 'row',
    justifyContent: 'center',
  },
  safeArea: {
    flex: 1,
    maxWidth: MaxContentWidth,
  },
  listContent: {
    padding: Spacing.three,
    gap: Spacing.two,
  },
  header: {
    gap: Spacing.three,
    marginBottom: Spacing.two,
  },
  titleRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  ingestRow: {
    flexDirection: 'row',
    gap: Spacing.two,
  },
  pasteRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.two,
  },
  input: {
    flex: 1,
    borderRadius: Spacing.two,
    paddingHorizontal: Spacing.three,
    paddingVertical: Spacing.two + Spacing.half,
    fontSize: 15,
    minHeight: 40,
  },
  tray: {
    gap: Spacing.two,
  },
  chipRow: {
    flexDirection: 'row',
    gap: Spacing.two,
  },
  empty: {
    textAlign: 'center',
    marginTop: Spacing.five,
    paddingHorizontal: Spacing.four,
  },
});
