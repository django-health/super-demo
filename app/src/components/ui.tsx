import type { ReactNode } from 'react';
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';

export const colors = {
  background: '#f6f7f9',
  card: '#ffffff',
  text: '#1a1d21',
  muted: '#6b7280',
  primary: '#208AEF',
  danger: '#dc2626',
  success: '#16a34a',
  border: '#e5e7eb',
};

export function Screen({ children }: { children: ReactNode }) {
  return (
    <ScrollView
      style={{ flex: 1, backgroundColor: colors.background }}
      contentContainerStyle={styles.screenContent}
    >
      {children}
    </ScrollView>
  );
}

export function Card({ children }: { children: ReactNode }) {
  return <View style={styles.card}>{children}</View>;
}

export function Title({ children }: { children: ReactNode }) {
  return <Text style={styles.title}>{children}</Text>;
}

export function Subtle({ children }: { children: ReactNode }) {
  return <Text style={styles.subtle}>{children}</Text>;
}

export function Button({
  label,
  onPress,
  variant = 'primary',
  busy = false,
  disabled = false,
}: {
  label: string;
  onPress: () => void;
  variant?: 'primary' | 'secondary' | 'danger';
  busy?: boolean;
  disabled?: boolean;
}) {
  const background =
    variant === 'primary'
      ? colors.primary
      : variant === 'danger'
        ? colors.danger
        : colors.card;
  const color = variant === 'secondary' ? colors.text : '#fff';
  return (
    <Pressable
      onPress={onPress}
      disabled={disabled || busy}
      style={({ pressed }) => [
        styles.button,
        { backgroundColor: background, opacity: pressed || disabled || busy ? 0.6 : 1 },
        variant === 'secondary' && { borderWidth: 1, borderColor: colors.border },
      ]}
    >
      {busy ? (
        <ActivityIndicator color={color} size="small" />
      ) : (
        <Text style={[styles.buttonLabel, { color }]}>{label}</Text>
      )}
    </Pressable>
  );
}

export function Badge({ label, tone }: { label: string; tone: 'ok' | 'off' | 'info' }) {
  const background =
    tone === 'ok' ? '#dcfce7' : tone === 'info' ? '#dbeafe' : '#f3f4f6';
  const color = tone === 'ok' ? '#166534' : tone === 'info' ? '#1e40af' : colors.muted;
  return (
    <View style={[styles.badge, { backgroundColor: background }]}>
      <Text style={{ color, fontSize: 12, fontWeight: '600' }}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  screenContent: {
    padding: 16,
    gap: 12,
    maxWidth: 720,
    width: '100%',
    alignSelf: 'center',
  },
  card: {
    backgroundColor: colors.card,
    borderRadius: 12,
    padding: 16,
    gap: 8,
    borderWidth: 1,
    borderColor: colors.border,
  },
  title: { fontSize: 17, fontWeight: '700', color: colors.text },
  subtle: { fontSize: 13, color: colors.muted },
  button: {
    borderRadius: 10,
    paddingVertical: 12,
    paddingHorizontal: 16,
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: 44,
  },
  buttonLabel: { fontSize: 15, fontWeight: '600' },
  badge: {
    borderRadius: 999,
    paddingHorizontal: 10,
    paddingVertical: 3,
    alignSelf: 'flex-start',
  },
});
