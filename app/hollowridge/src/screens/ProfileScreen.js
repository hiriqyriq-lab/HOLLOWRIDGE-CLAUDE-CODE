import React from 'react';
import { View, Text, ScrollView, StyleSheet, TouchableOpacity } from 'react-native';
import { colors, fonts, spacing } from '../theme';
import { signOut } from '../services/auth';

export default function ProfileScreen({ user, onSignOut }) {
  async function handleSignOut() {
    await signOut();
    onSignOut();
  }

  return (
    <ScrollView style={s.root} contentContainerStyle={s.content}>
      <View style={s.avatar}>
        <Text style={s.avatarText}>◈</Text>
      </View>
      <Text style={s.contact}>{user?.contact || '—'}</Text>
      <Text style={s.status}>PEAK PIONEER · ACTIVE</Text>

      <View style={s.divider} />

      <Text style={s.sectionHead}>LATTICE POSITION</Text>
      <View style={s.statRow}>
        <View style={s.stat}><Text style={s.statVal}>813</Text><Text style={s.statLabel}>TOTAL NODES</Text></View>
        <View style={s.stat}><Text style={s.statVal}>396+</Text><Text style={s.statLabel}>COORDINATES</Text></View>
        <View style={s.stat}><Text style={s.statVal}>13×</Text><Text style={s.statLabel}>HOURLY SOLVES</Text></View>
      </View>

      <View style={s.divider} />

      <Text style={s.sectionHead}>NOTIFICATION SETTINGS</Text>
      {['Drop Alerts', 'Lore Updates', 'Lattice Solves', 'FORGE Advisories'].map(label => (
        <View key={label} style={s.settingRow}>
          <Text style={s.settingLabel}>{label}</Text>
          <Text style={s.settingVal}>ON</Text>
        </View>
      ))}

      <View style={s.divider} />

      <TouchableOpacity style={s.signOutBtn} onPress={handleSignOut}>
        <Text style={s.signOutText}>SIGN OUT</Text>
      </TouchableOpacity>
    </ScrollView>
  );
}

const s = StyleSheet.create({
  root: { flex: 1, backgroundColor: colors.black },
  content: { padding: spacing.lg, alignItems: 'center' },
  avatar: {
    width: 80, height: 80, borderRadius: 40, borderWidth: 1, borderColor: colors.ridge,
    justifyContent: 'center', alignItems: 'center', marginBottom: spacing.md, marginTop: spacing.md,
  },
  avatarText: { color: colors.ridge, fontSize: 32 },
  contact: { color: colors.white, fontSize: 16, fontWeight: '600' },
  status: { color: colors.ridge, fontSize: 10, ...fonts.heading, marginTop: 4 },
  divider: { height: 1, backgroundColor: colors.border, width: '100%', marginVertical: spacing.lg },
  sectionHead: { color: colors.muted, fontSize: 10, ...fonts.heading, alignSelf: 'flex-start', marginBottom: spacing.md },
  statRow: { flexDirection: 'row', justifyContent: 'space-around', width: '100%' },
  stat: { alignItems: 'center' },
  statVal: { color: colors.ridge, fontSize: 22, fontWeight: '800' },
  statLabel: { color: colors.muted, fontSize: 9, ...fonts.heading, marginTop: 2 },
  settingRow: { flexDirection: 'row', justifyContent: 'space-between', width: '100%', paddingVertical: spacing.sm, borderBottomWidth: 1, borderBottomColor: colors.border },
  settingLabel: { color: colors.white, fontSize: 13 },
  settingVal: { color: colors.success, fontSize: 11, fontWeight: '800' },
  signOutBtn: { borderWidth: 1, borderColor: colors.border, borderRadius: 4, padding: spacing.md, width: '100%', alignItems: 'center', marginTop: spacing.sm },
  signOutText: { color: colors.muted, ...fonts.heading, fontSize: 12 },
});
