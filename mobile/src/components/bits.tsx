/** Small shared presentational pieces: chips, badges, progress bar, buttons. */

import React from 'react';
import { Pressable, StyleSheet, View, type ViewStyle } from 'react-native';

import { ThemedText } from '@/components/themed-text';
import { Spacing } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';

export const ACCENT = '#208AEF';
export const DANGER = '#D64545';
export const WARNING_BG = 'rgba(214, 158, 46, 0.15)';
export const WARNING_TEXT = '#B7791F';

export function Chip({
  label,
  active = false,
  onPress,
}: {
  label: string;
  active?: boolean;
  onPress?: () => void;
}) {
  const theme = useTheme();
  return (
    <Pressable
      onPress={onPress}
      disabled={!onPress}
      style={[
        styles.chip,
        { backgroundColor: active ? ACCENT : theme.backgroundElement },
      ]}
    >
      <ThemedText type="small" style={active ? styles.chipActiveText : undefined}>
        {label}
      </ThemedText>
    </Pressable>
  );
}

export function ProgressBar({ progress }: { progress: number }) {
  const theme = useTheme();
  const clamped = Math.max(0, Math.min(1, progress));
  return (
    <View style={[styles.progressTrack, { backgroundColor: theme.backgroundSelected }]}>
      <View style={[styles.progressFill, { width: `${clamped * 100}%` }]} />
    </View>
  );
}

export function Button({
  label,
  onPress,
  kind = 'primary',
  style,
}: {
  label: string;
  onPress: () => void;
  kind?: 'primary' | 'secondary' | 'danger';
  style?: ViewStyle;
}) {
  const theme = useTheme();
  const background =
    kind === 'primary' ? ACCENT : kind === 'danger' ? DANGER : theme.backgroundElement;
  const color = kind === 'secondary' ? theme.text : '#ffffff';
  return (
    <Pressable
      onPress={onPress}
      style={({ pressed }) => [
        styles.button,
        { backgroundColor: background, opacity: pressed ? 0.75 : 1 },
        style,
      ]}
    >
      <ThemedText type="smallBold" style={{ color }}>
        {label}
      </ThemedText>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  chip: {
    paddingHorizontal: Spacing.three,
    paddingVertical: Spacing.one + Spacing.half,
    borderRadius: 999,
  },
  chipActiveText: {
    color: '#ffffff',
  },
  progressTrack: {
    height: 4,
    borderRadius: 2,
    overflow: 'hidden',
    alignSelf: 'stretch',
  },
  progressFill: {
    height: 4,
    borderRadius: 2,
    backgroundColor: ACCENT,
  },
  button: {
    paddingHorizontal: Spacing.three,
    paddingVertical: Spacing.two + Spacing.half,
    borderRadius: Spacing.two,
    alignItems: 'center',
    justifyContent: 'center',
  },
});
