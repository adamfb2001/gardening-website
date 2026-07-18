import { useLocalSearchParams, useRouter } from 'expo-router';
import React from 'react';
import { Linking, ScrollView, StyleSheet, View } from 'react-native';

import { Button, Chip, WARNING_BG, WARNING_TEXT } from '@/components/bits';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { MaxContentWidth, Spacing } from '@/constants/theme';
import { confirmAsync } from '@/lib/confirm';
import { useClipNotes } from '@/lib/store';
import { platformLabel } from '@/lib/types';

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <View style={styles.section}>
      <ThemedText type="smallBold" themeColor="textSecondary">
        {title.toUpperCase()}
      </ThemedText>
      {children}
    </View>
  );
}

export default function NoteDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const { notes, deleteNote, toggleFavourite } = useClipNotes();
  const stored = notes.find((n) => n.id === id);

  if (!stored) {
    return (
      <ThemedView style={styles.missing}>
        <ThemedText themeColor="textSecondary">This note is no longer here.</ThemedText>
      </ThemedView>
    );
  }

  const { note } = stored;
  const entityRows = (
    [
      ['People', note.entities.people],
      ['Products', note.entities.products],
      ['Places', note.entities.places],
      ['Tools', note.entities.tools],
      ['Links mentioned', note.entities.links_mentioned],
    ] as const
  ).filter(([, items]) => items.length > 0);

  const handleDelete = async () => {
    const confirmed = await confirmAsync(
      'Delete note?',
      'This removes the note from your library on this device.',
    );
    if (confirmed) {
      deleteNote(stored.id);
      router.back();
    }
  };

  return (
    <ThemedView style={styles.container}>
      <ScrollView contentContainerStyle={styles.content}>
        <ThemedText type="title">{note.title}</ThemedText>

        <View style={styles.metaRow}>
          <Chip label={platformLabel(stored.platform)} />
          <Chip label={note.category} />
          <ThemedText type="small" themeColor="textSecondary">
            Saved {new Date(stored.createdAt).toLocaleDateString()}
          </ThemedText>
        </View>

        {note.caveats.length > 0 && (
          <View style={styles.caveats}>
            {note.caveats.map((caveat) => (
              <ThemedText key={caveat} type="small" style={styles.caveatText}>
                ⚠︎ {caveat}
              </ThemedText>
            ))}
          </View>
        )}

        <ThemedText>{note.summary}</ThemedText>

        {note.key_points.length > 0 && (
          <Section title="Key points">
            {note.key_points.map((point) => (
              <ThemedText key={point}>• {point}</ThemedText>
            ))}
          </Section>
        )}

        {note.steps.length > 0 && (
          <Section title="Steps">
            {note.steps.map((step) => (
              <ThemedText key={step.n}>
                {step.n}. {step.text}
              </ThemedText>
            ))}
          </Section>
        )}

        {note.quotes.length > 0 && (
          <Section title="Quotes">
            {note.quotes.map((quote) => (
              <ThemedText key={`${quote.timestamp_s}-${quote.text}`} type="small">
                “{quote.text}” — {Math.round(quote.timestamp_s)}s
              </ThemedText>
            ))}
          </Section>
        )}

        {entityRows.length > 0 && (
          <Section title="Mentioned">
            {entityRows.map(([label, items]) => (
              <ThemedText key={label} type="small">
                <ThemedText type="smallBold">{label}: </ThemedText>
                {items.join(', ')}
              </ThemedText>
            ))}
          </Section>
        )}

        {note.tags.length > 0 && (
          <Section title="Tags">
            <View style={styles.tagRow}>
              {note.tags.map((tag) => (
                <Chip key={tag} label={`#${tag}`} />
              ))}
            </View>
          </Section>
        )}

        <Section title="Confidence">
          <ThemedText type="small" themeColor="textSecondary">
            audio {Math.round(note.confidence.audio * 100)}% · visual{' '}
            {Math.round(note.confidence.visual * 100)}% · overall{' '}
            {Math.round(note.confidence.overall * 100)}%
          </ThemedText>
        </Section>

        <View style={styles.actions}>
          <Button
            label="Open original"
            onPress={() => Linking.openURL(stored.sourceUrl).catch(() => {})}
          />
          <Button
            label={stored.favourite ? '★ Unfavourite' : '☆ Favourite'}
            kind="secondary"
            onPress={() => toggleFavourite(stored.id)}
          />
          <Button label="Delete" kind="danger" onPress={handleDelete} />
        </View>

        <ThemedText type="small" themeColor="textSecondary">
          Source: {stored.sourceUrl}
        </ThemedText>
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
    gap: Spacing.three,
    maxWidth: MaxContentWidth,
    alignSelf: 'center',
    width: '100%',
  },
  missing: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  metaRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.two,
    flexWrap: 'wrap',
  },
  caveats: {
    backgroundColor: WARNING_BG,
    borderRadius: Spacing.two,
    padding: Spacing.three,
    gap: Spacing.one,
  },
  caveatText: {
    color: WARNING_TEXT,
  },
  section: {
    gap: Spacing.two,
  },
  tagRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.two,
  },
  actions: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.two,
  },
});
