import { Alert, Platform } from 'react-native';

/** Alert.alert is a no-op on react-native-web, so fall back to window.confirm. */
export function confirmAsync(title: string, message: string, okText = 'Delete'): Promise<boolean> {
  if (Platform.OS === 'web') {
    return Promise.resolve(
      typeof window !== 'undefined' && window.confirm(`${title}\n\n${message}`),
    );
  }
  return new Promise((resolve) => {
    Alert.alert(title, message, [
      { text: 'Cancel', style: 'cancel', onPress: () => resolve(false) },
      { text: okText, style: 'destructive', onPress: () => resolve(true) },
    ]);
  });
}
