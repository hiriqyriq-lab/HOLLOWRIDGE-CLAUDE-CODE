import React from 'react';
import { View, Text, ScrollView, StyleSheet, TouchableOpacity, ImageBackground } from 'react-native';
import { colors, fonts, spacing } from '../theme';

const DROPS = [
  { id: '1', title: 'ZERO-POINT HOODIE', subtitle: 'Peak Pioneer Series I', status: 'LIVE', price: '$148' },
  { id: '2', title: 'GENOME PULLOVER',   subtitle: 'Contrapolation Cut',     status: 'LIVE', price: '$132' },
  { id: '3', title: 'LATTICE COACH',     subtitle: 'Terminal-X Edition',     status: 'DROP SOON', price: 'TBA' },
  { id: '4', title: 'TOTEM CARGO',       subtitle: '13-Ring Legacy Fit',     status: 'DROP SOON', price: 'TBA' },
];

export default function HomeScreen({ navigation }) {
  return (
    <ScrollView style={s.root} contentContainerStyle={s.content}>
      <Text style={s.wordmark}>HOLLOW RIDGE</Text>
      <Text style={s.tagline}>ZERO-POINT PEAK ARCHITECTURE</Text>

      <View style={s.divider} />

      <Text style={s.sectionHead}>CURRENT DROPS</Text>
      {DROPS.map(drop => (
        <TouchableOpacity key={drop.id} style={s.card} onPress={() => navigation.navigate('Drop', { drop })}>
          <View style={s.cardLeft}>
            <Text style={s.dropTitle}>{drop.title}</Text>
            <Text style={s.dropSub}>{drop.subtitle}</Text>
          </View>
          <View style={s.cardRight}>
            <Text style={[s.status, drop.status === 'LIVE' ? s.live : s.soon]}>{drop.status}</Text>
            <Text style={s.price}>{drop.price}</Text>
          </View>
        </TouchableOpacity>
      ))}

      <View style={s.divider} />

      <TouchableOpacity style={s.loreBtn} onPress={() => navigation.navigate('Lore')}>
        <Text style={s.loreBtnText}>ENTER THE LORE ›</Text>
      </TouchableOpacity>
    </ScrollView>
  );
}

const s = StyleSheet.create({
  root: { flex: 1, backgroundColor: colors.black },
  content: { padding: spacing.lg, paddingBottom: spacing.xl },
  wordmark: { color: colors.ridge, fontSize: 28, ...fonts.heading, textAlign: 'center', marginTop: spacing.lg },
  tagline: { color: colors.muted, fontSize: 10, ...fonts.heading, textAlign: 'center', marginBottom: spacing.lg },
  divider: { height: 1, backgroundColor: colors.border, marginVertical: spacing.lg },
  sectionHead: { color: colors.white, fontSize: 11, ...fonts.heading, marginBottom: spacing.md },
  card: {
    backgroundColor: colors.card, borderWidth: 1, borderColor: colors.border,
    borderRadius: 4, padding: spacing.md, marginBottom: spacing.sm,
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
  },
  cardLeft: { flex: 1 },
  cardRight: { alignItems: 'flex-end' },
  dropTitle: { color: colors.white, fontWeight: '700', letterSpacing: 1, fontSize: 14 },
  dropSub: { color: colors.muted, fontSize: 11, marginTop: 2 },
  status: { fontSize: 10, fontWeight: '800', letterSpacing: 1 },
  live: { color: colors.success },
  soon: { color: colors.ridgeDim },
  price: { color: colors.ridge, fontWeight: '700', fontSize: 14, marginTop: 4 },
  loreBtn: {
    borderWidth: 1, borderColor: colors.ridge, borderRadius: 4,
    padding: spacing.md, alignItems: 'center', marginTop: spacing.sm,
  },
  loreBtnText: { color: colors.ridge, ...fonts.heading, fontSize: 13 },
});
