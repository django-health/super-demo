import { useCallback, useEffect, useState } from 'react';
import { Alert, Platform, RefreshControl, ScrollView, StyleSheet, Text, View } from 'react-native';
import * as WebBrowser from 'expo-web-browser';

import { Badge, Button, Card, Subtle, Title, colors } from '@/components/ui';
import { api, type Connections } from '@/lib/api';
import { useAuth } from '@/lib/auth';

function notify(title: string, message: string) {
  if (Platform.OS === 'web') {
    // eslint-disable-next-line no-alert
    window.alert(`${title}\n\n${message}`);
  } else {
    Alert.alert(title, message);
  }
}

export default function ConnectionsScreen() {
  const { token } = useAuth();
  const [connections, setConnections] = useState<Connections | null>(null);
  const [busySlug, setBusySlug] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async () => {
    if (!token) return;
    try {
      setConnections(await api.connections(token));
    } catch {
      // leave the previous state in place
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

  const connect = async (slug: string) => {
    if (!token) return;
    setBusySlug(slug);
    try {
      const { url } = await api.providerConnect(token, slug);
      if (Platform.OS === 'web') {
        window.open(url, '_blank');
      } else {
        await WebBrowser.openBrowserAsync(url);
      }
      await load();
    } catch (exc) {
      notify('Connect failed', exc instanceof Error ? exc.message : String(exc));
    } finally {
      setBusySlug(null);
    }
  };

  const sync = async (slug: string) => {
    if (!token) return;
    setBusySlug(slug);
    try {
      const result = await api.providerSync(token, slug, 7);
      const detail = Object.entries(result.counts)
        .map(([key, count]) => `${key}: ${count}`)
        .join('\n');
      notify(`Synced ${result.total} records`, detail || 'Nothing new.');
      await load();
    } catch (exc) {
      notify('Sync failed', exc instanceof Error ? exc.message : String(exc));
    } finally {
      setBusySlug(null);
    }
  };

  const disconnect = async (slug: string) => {
    if (!token) return;
    setBusySlug(slug);
    try {
      await api.providerDisconnect(token, slug);
      await load();
    } catch (exc) {
      notify('Disconnect failed', exc instanceof Error ? exc.message : String(exc));
    } finally {
      setBusySlug(null);
    }
  };

  return (
    <ScrollView
      style={{ flex: 1, backgroundColor: colors.background }}
      contentContainerStyle={styles.content}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={refresh} />}
    >
      <Subtle>
        Cloud providers sync server-side through the django-health packages.
        Device pipelines (below) are fed by phones pushing HealthKit / Health
        Connect data.
      </Subtle>

      {connections?.providers.map((provider) => (
        <Card key={provider.slug}>
          <View style={styles.cardHeader}>
            <Title>{provider.label}</Title>
            {provider.connected ? (
              <Badge label="connected" tone="ok" />
            ) : provider.configured ? (
              <Badge label="not connected" tone="off" />
            ) : (
              <Badge label="no credentials" tone="off" />
            )}
          </View>
          <Subtle>
            {provider.records.toLocaleString()} records ·{' '}
            {provider.workouts.toLocaleString()} workouts
          </Subtle>
          <View style={styles.buttonRow}>
            {provider.connected ? (
              <>
                <Button
                  label="Sync last 7 days"
                  onPress={() => sync(provider.slug)}
                  busy={busySlug === provider.slug}
                />
                <Button
                  label="Disconnect"
                  variant="danger"
                  onPress={() => disconnect(provider.slug)}
                  busy={busySlug === provider.slug}
                />
              </>
            ) : (
              <Button
                label={`Connect ${provider.label}`}
                onPress={() => connect(provider.slug)}
                busy={busySlug === provider.slug}
                disabled={!provider.configured}
              />
            )}
          </View>
        </Card>
      ))}

      <Card>
        <Title>Device pipelines</Title>
        {connections?.devices.length ? (
          connections.devices.map((device) => (
            <View key={device.data_source} style={styles.deviceRow}>
              <View style={{ flex: 1 }}>
                <Text style={{ color: colors.text, fontWeight: '600' }}>
                  {device.data_source}
                  {device.device_brand ? ` (${device.device_brand})` : ''}
                </Text>
                <Subtle>
                  {device.records.toLocaleString()} records · last sync{' '}
                  {device.last_synced_at
                    ? new Date(device.last_synced_at).toLocaleString()
                    : 'never'}
                </Subtle>
              </View>
              <Badge
                label={device.status}
                tone={device.status === 'active' ? 'ok' : 'off'}
              />
            </View>
          ))
        ) : (
          <Subtle>
            Nothing yet — push data from the “This Device” tab on a phone.
          </Subtle>
        )}
      </Card>
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
  deviceRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    paddingVertical: 6,
  },
});
