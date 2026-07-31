import { Redirect, Tabs } from 'expo-router';
import { Text, type ColorValue } from 'react-native';

import { colors } from '@/components/ui';
import { useAuth } from '@/lib/auth';

function TabIcon({ glyph, color }: { glyph: string; color: ColorValue }) {
  return <Text style={{ fontSize: 20, color }}>{glyph}</Text>;
}

export default function TabsLayout() {
  const { token, ready } = useAuth();

  if (!ready) return null;
  if (!token) return <Redirect href="/login" />;

  return (
    <Tabs
      screenOptions={{
        tabBarActiveTintColor: colors.primary,
        headerTitleStyle: { fontWeight: '700' },
      }}
    >
      <Tabs.Screen
        name="index"
        options={{
          title: 'Dashboard',
          tabBarIcon: ({ color }) => <TabIcon glyph="📊" color={color} />,
        }}
      />
      <Tabs.Screen
        name="connections"
        options={{
          title: 'Connections',
          tabBarIcon: ({ color }) => <TabIcon glyph="🔗" color={color} />,
        }}
      />
      <Tabs.Screen
        name="device"
        options={{
          title: 'This Device',
          tabBarIcon: ({ color }) => <TabIcon glyph="📱" color={color} />,
        }}
      />
    </Tabs>
  );
}
