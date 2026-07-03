import React, { useEffect, useState } from 'react';
import { View, Text, FlatList, StyleSheet, TouchableOpacity } from 'react-native';
import * as Notifications from 'expo-notifications';
import { colors, fonts, spacing } from '../theme';
import { registerForPushNotifications } from '../services/notifications';

const MOCK_NOTIFICATIONS = [
  { id: '1', type: 'DROP', title: 'ZERO-POINT HOODIE IS LIVE', body: 'Pioneer Series I is now available. Limited units.', ts: Date.now() - 1000 * 60 * 5, read: false },
  { id: '2', type: 'LORE', title: 'NEW COORDINATE UNLOCKED', body: 'Coordinate 397 added to the operational genome.', ts: Date.now() - 1000 * 60 * 60 * 2, read: false },
  { id: '3', type: 'SYSTEM', title: 'LATTICE AUTOSOLVE UPDATE', body: '613 nodes solved. Contrapolation archive updated.', ts: Date.now() - 1000 * 60 * 60 * 6, read: true },
  { id: '4', type: 'DROP', title: 'LATTICE COACH — DROP SOON', body: 'Terminal-X Edition dropping within 72 hours. Enable alerts.', ts: Date.now() - 1000 * 60 * 60 * 24, read: true },
];

const TYPE_COLORS = { DROP: colors.success, LORE: colors.ridge, SYSTEM: colors.muted };

function timeAgo(ts) {
  const diff = Date.now() - ts;
  if (diff < 60000) return 'just now';
  if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
  return `${Math.floor(diff / 86400000)}d ago`;
}

export default function NotificationsScreen() {
  const [pushToken, setPushToken] = useState(null);
  const [notifications, setNotifications] = useState(MOCK_NOTIFICATIONS);

  useEffect(() => {
    registerForPushNotifications().then(setPushToken);
    const sub = Notifications.addNotificationReceivedListener(notif => {
      setNotifications(prev => [{
        id: String(Date.now()),
        type: notif.request.content.data?.type || 'SYSTEM',
        title: notif.request.content.title,
        body: notif.request.content.body,
        ts: Date.now(),
        read: false,
      }, ...prev]);
    });
    return () => sub.remove();
  }, []);

  function markRead(id) {
    setNotifications(prev => prev.map(n => n.id === id ? { ...n, read: true } : n));
  }

  const unread = notifications.filter(n => !n.read).length;

  return (
    <View style={s.root}>
      <View style={s.header}>
        <Text style={s.headTitle}>TRANSMISSIONS</Text>
        {unread > 0 && <View style={s.badge}><Text style={s.badgeText}>{unread}</Text></View>}
      </View>
      {pushToken ? (
        <Text style={s.tokenNote}>Push active · {pushToken.slice(0, 24)}…</Text>
      ) : (
        <Text style={s.tokenNote}>Enable push notifications for drop alerts</Text>
      )}
      <FlatList
        data={notifications}
        keyExtractor={item => item.id}
        contentContainerStyle={s.list}
        renderItem={({ item }) => (
          <TouchableOpacity
            style={[s.card, !item.read && s.cardUnread]}
            onPress={() => markRead(item.id)}
            activeOpacity={0.8}
          >
            <View style={s.cardTop}>
              <Text style={[s.type, { color: TYPE_COLORS[item.type] || colors.muted }]}>{item.type}</Text>
              <Text style={s.ts}>{timeAgo(item.ts)}</Text>
              {!item.read && <View style={s.dot} />}
            </View>
            <Text style={s.title}>{item.title}</Text>
            <Text style={s.body}>{item.body}</Text>
          </TouchableOpacity>
        )}
      />
    </View>
  );
}

const s = StyleSheet.create({
  root: { flex: 1, backgroundColor: colors.black },
  header: { flexDirection: 'row', alignItems: 'center', padding: spacing.lg, paddingBottom: spacing.sm },
  headTitle: { color: colors.white, fontSize: 18, ...fonts.heading, flex: 1 },
  badge: { backgroundColor: colors.ridge, borderRadius: 10, paddingHorizontal: 8, paddingVertical: 2 },
  badgeText: { color: colors.black, fontWeight: '800', fontSize: 11 },
  tokenNote: { color: colors.muted, fontSize: 10, paddingHorizontal: spacing.lg, marginBottom: spacing.sm, ...fonts.mono },
  list: { padding: spacing.md, paddingTop: 0 },
  card: {
    backgroundColor: colors.card, borderWidth: 1, borderColor: colors.border,
    borderRadius: 4, padding: spacing.md, marginBottom: spacing.sm,
  },
  cardUnread: { borderColor: colors.ridgeDim },
  cardTop: { flexDirection: 'row', alignItems: 'center', marginBottom: 4 },
  type: { fontSize: 9, fontWeight: '800', letterSpacing: 1.5, flex: 1 },
  ts: { color: colors.muted, fontSize: 11 },
  dot: { width: 6, height: 6, borderRadius: 3, backgroundColor: colors.ridge, marginLeft: spacing.sm },
  title: { color: colors.white, fontWeight: '700', fontSize: 13, letterSpacing: 0.5, marginBottom: 4 },
  body: { color: colors.muted, fontSize: 12, lineHeight: 18 },
});
