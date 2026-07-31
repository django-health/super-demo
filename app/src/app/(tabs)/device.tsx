import { useEffect, useState } from 'react';
import { Platform, ScrollView, StyleSheet, Text, View } from 'react-native';

import { Badge, Button, Card, Subtle, Title, colors } from '@/components/ui';
import { reader, type HealthReadResult } from '@/health';
import { api } from '@/lib/api';
import { useAuth } from '@/lib/auth';

const DAYS = 7;

export default function DeviceScreen() {
  const { token } = useAuth();
  const [available, setAvailable] = useState<boolean | null>(null);
  const [authorized, setAuthorized] = useState(false);
  const [preview, setPreview] = useState<HealthReadResult | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    reader.available().then(setAvailable);
  }, []);

  const requestPermissions = async () => {
    setBusy(true);
    try {
      setAuthorized(await reader.requestPermissions());
    } catch (exc) {
      setStatus(exc instanceof Error ? exc.message : String(exc));
    } finally {
      setBusy(false);
    }
  };

  const read = async () => {
    setBusy(true);
    setStatus(null);
    try {
      setPreview(await reader.read(DAYS));
    } catch (exc) {
      setStatus(exc instanceof Error ? exc.message : String(exc));
    } finally {
      setBusy(false);
    }
  };

  const push = async () => {
    if (!token || !preview) return;
    setBusy(true);
    setStatus(null);
    try {
      let message = '';
      if (preview.records.length > 0) {
        const result = await api.pushRecords(
          token,
          preview.source,
          preview.deviceBrand,
          preview.records,
        );
        message += `${result.ingested} records`;
      }
      if (preview.workouts.length > 0) {
        const result = await api.pushWorkouts(
          token,
          preview.source,
          preview.deviceBrand,
          preview.workouts,
        );
        message += `${message ? ' + ' : ''}${result.ingested} workouts`;
      }
      setStatus(
        message
          ? `Pushed ${message} to the backend. Check the dashboard on your other devices!`
          : 'Nothing to push.',
      );
    } catch (exc) {
      setStatus(exc instanceof Error ? exc.message : String(exc));
    } finally {
      setBusy(false);
    }
  };

  const recordTypeCounts = new Map<string, number>();
  for (const record of preview?.records ?? []) {
    const short = record.type.replace(/^HK(QuantityTypeIdentifier|CategoryTypeIdentifier)/, '');
    recordTypeCounts.set(short, (recordTypeCounts.get(short) ?? 0) + 1);
  }

  return (
    <ScrollView
      style={{ flex: 1, backgroundColor: colors.background }}
      contentContainerStyle={styles.content}
    >
      <Card>
        <View style={styles.cardHeader}>
          <Title>{reader.label}</Title>
          {available === null ? null : available ? (
            <Badge label="available" tone="ok" />
          ) : (
            <Badge label="unavailable" tone="off" />
          )}
        </View>
        <Subtle>
          {Platform.OS === 'web'
            ? 'Browsers have no on-device health store. Open this tab in the iOS or Android app to push device data; this web build still shows everything synced by your other devices.'
            : `Read the last ${DAYS} days from ${reader.label} and push them to the backend as ${Platform.OS === 'ios' ? 'apple_health' : 'health_connect'}.`}
        </Subtle>
        {available ? (
          <View style={styles.buttonRow}>
            <Button
              label={authorized ? 'Permissions granted' : 'Grant permissions'}
              variant={authorized ? 'secondary' : 'primary'}
              onPress={requestPermissions}
              busy={busy && !preview}
            />
            <Button label={`Read ${DAYS} days`} onPress={read} busy={busy} />
          </View>
        ) : null}
      </Card>

      {preview ? (
        <Card>
          <Title>Ready to push</Title>
          {[...recordTypeCounts.entries()].map(([type, count]) => (
            <View key={type} style={styles.previewRow}>
              <Text style={{ color: colors.text }}>{type}</Text>
              <Text style={{ color: colors.muted }}>{count.toLocaleString()}</Text>
            </View>
          ))}
          <View style={styles.previewRow}>
            <Text style={{ color: colors.text }}>Workouts</Text>
            <Text style={{ color: colors.muted }}>
              {preview.workouts.length.toLocaleString()}
            </Text>
          </View>
          <Button
            label={`Push to backend as ${preview.source}`}
            onPress={push}
            busy={busy}
            disabled={preview.records.length + preview.workouts.length === 0}
          />
        </Card>
      ) : null}

      {status ? <Text style={{ color: colors.text }}>{status}</Text> : null}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  content: { padding: 16, gap: 12, maxWidth: 720, width: '100%', alignSelf: 'center' },
  cardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  buttonRow: { flexDirection: 'row', gap: 8, flexWrap: 'wrap' },
  previewRow: { flexDirection: 'row', justifyContent: 'space-between' },
});
