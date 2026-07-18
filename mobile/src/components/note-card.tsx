import { Link } from 'expo-router';
import React from 'react';
import { Pressable, StyleSheet, View } from 'react-native';

import { Chip } from '@/components/bits';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { Spacing } from '@/constants/theme';
import { platformLabel, type StoredNote } from '@/lib/types';

export function NoteCard({ note }: { note: StoredNote }) {
  return (
    <Link href={{ pathname: '/note/[id]', params: { id: note.id } }} asChild>
      <Pressable>
        <ThemedView type="backgroundElement" style={styles.card}>
          <ThemedText type="subtitle">
            {note.favourite ? '★ ' : ''}
            {note.note.title}
          </ThemedText>
          <ThemedText type="small" themeColor="textSecondary" numberOfLines={2}>
            {note.note.summary}
          </ThemedText>
          <View style={styles.metaRow}>
            <Chip label={platformLabel(note.platform)} />
            <Chip label={note.note.category} />
            <ThemedText type="small" themeColor="textSecondary">
              {new Date(note.createdAt).toLocaleDateString()}
            </ThemedText>
          </View>
        </ThemedView>
      </Pressable>
    </Link>
  );
}

const styles = StyleSheet.create({
  card: {
    borderRadius: Spacing.three,
    padding: Spacing.three,
    gap: Spacing.two,
  },
  metaRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.two,
    flexWrap: 'wrap',
  },
});
