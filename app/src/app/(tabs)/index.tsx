import { useCallback, useEffect, useState } from 'react';
import { RefreshControl, ScrollView, StyleSheet, Text, View } from 'react-native';

import { Button, Card, Subtle, Title, colors } from '@/components/ui';
import { api, type Summary } from '@/lib/api';
import { useAuth } from '@/lib/auth';

const DAYS = 14;

function BarChart({
  values,
  color,
  format,
}: {
  values: (number | null)[];
  color: string;
  format: (value: number) => string;
}) {
  const max = Math.max(...values.map((value) => value ?? 0), 1);
  return (
    <View style={styles.chartRow}>
      {values.map((value, index) => (
        <View key={index} style={styles.chartColumn}>
          <View
            style={[
              styles.bar,
              {
                height: `${Math.max(((value ?? 0) / max) * 100, 2)}%`,
                backgroundColor: value === null ? colors.border : color,
              },
            ]}
          />
        </View>
      ))}
    </View>
  );
}

function latest(values: (number | null)[]): number | null {
  for (let index = values.length - 1; index >= 0; index -= 1) {
    if (values[index] !== null) return values[index];
  }
  return null;
}

export default function Dashboard() {
  const { token, username, signOut } = useAuth();
  const [summary, setSummary] = useState<Summary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async () => {
    if (!token) return;
    try {
      setSummary(await api.summary(token, DAYS));
      setError(null);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : 'Failed to load');
    }
  }, [token]);

  useEffect(() => {
    load();
  }, [load]);

  const refresh = async () => {
    setRefreshing(true);
    await load();
    setRefreshing(false);
  };

  const days = summary?.days ?? [];
  const steps = days.map((day) => day.steps);
  const active = days.map((day) => day.active_kcal);
  const sleep = days.map((day) => day.sleep_hours);

  return (
    <ScrollView
      style={{ flex: 1, backgroundColor: colors.background }}
      contentContainerStyle={styles.content}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={refresh} />}
    >
      <Subtle>
        Signed in as {username}. Last {DAYS} days, merged across every connected
        source — pull to refresh after syncing another device.
      </Subtle>
      {error ? <Text style={{ color: colors.danger }}>{error}</Text> : null}

      <Card>
        <Title>👟 Steps</Title>
        <Text style={styles.metric}>
          {latest(steps) !== null ? Math.round(latest(steps)!).toLocaleString() : '—'}
        </Text>
        <BarChart values={steps} color={colors.primary} format={(v) => `${v}`} />
      </Card>

      <Card>
        <Title>🔥 Active energy (kcal)</Title>
        <Text style={styles.metric}>
          {latest(active) !== null ? Math.round(latest(active)!).toLocaleString() : '—'}
        </Text>
        <BarChart values={active} color="#f59e0b" format={(v) => `${v}`} />
      </Card>

      <Card>
        <Title>😴 Sleep (hours)</Title>
        <Text style={styles.metric}>
          {latest(sleep) !== null ? latest(sleep)!.toFixed(1) : '—'}
        </Text>
        <BarChart values={sleep} color="#8b5cf6" format={(v) => v.toFixed(1)} />
      </Card>

      <Card>
        <Title>Daily detail</Title>
        {[...days].reverse().map((day) => (
          <View key={day.date} style={styles.dayRow}>
            <Text style={styles.dayDate}>{day.date.slice(5)}</Text>
            <Text style={styles.dayValue}>
              {day.steps !== null ? `${Math.round(day.steps).toLocaleString()} st` : '—'}
            </Text>
            <Text style={styles.dayValue}>
              {day.active_kcal !== null ? `${Math.round(day.active_kcal)} kcal` : '—'}
            </Text>
            <Text style={styles.dayValue}>
              {day.sleep_hours !== null ? `${day.sleep_hours.toFixed(1)} h` : '—'}
            </Text>
          </View>
        ))}
      </Card>

      <Button label="Sign out" variant="secondary" onPress={signOut} />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  content: { padding: 16, gap: 12, maxWidth: 720, width: '100%', alignSelf: 'center' },
  metric: { fontSize: 28, fontWeight: '800', color: colors.text },
  chartRow: { flexDirection: 'row', alignItems: 'flex-end', height: 72, gap: 3 },
  chartColumn: { flex: 1, height: '100%', justifyContent: 'flex-end' },
  bar: { borderRadius: 3, width: '100%' },
  dayRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 4,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: colors.border,
  },
  dayDate: { color: colors.muted, fontVariant: ['tabular-nums'], width: 52 },
  dayValue: { color: colors.text, fontVariant: ['tabular-nums'] },
});
