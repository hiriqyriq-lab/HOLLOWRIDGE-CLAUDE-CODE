import React from 'react';
import { View, Text, ScrollView, StyleSheet, TouchableOpacity } from 'react-native';
import { colors, fonts, spacing } from '../theme';

export default function DropScreen({ route }) {
  const { drop } = route.params;
  return (
    <ScrollView style={s.root} contentContainerStyle={s.content}>
      <View style={s.hero}>
        <Text style={s.heroLabel}>HOLLOW RIDGE × {drop.subtitle.toUpperCase()}</Text>
      </View>
      <Text style={s.title}>{drop.title}</Text>
      <Text style={s.sub}>{drop.subtitle}</Text>
      <View style={s.row}>
        <Text style={[s.status, drop.status === 'LIVE' ? s.live : s.soon]}>{drop.status}</Text>
        <Text style={s.price}>{drop.price}</Text>
      </View>
      <View style={s.divider} />
      <Text style={s.descHead}>PIECE DOCTRINE</Text>
      <Text style={s.desc}>
        Every Hollow Ridge piece is a coordinate in the operational genome. Not a product —
        a lattice node. Wearing it activates your position within the peak pioneer framework.
        Density-first construction. Zero excess.
      </Text>
      {drop.status === 'LIVE' && (
        <TouchableOpacity style={s.btn}>
          <Text style={s.btnText}>ACQUIRE THIS PIECE</Text>
        </TouchableOpacity>
      )}
      {drop.status !== 'LIVE' && (
        <TouchableOpacity style={s.notifyBtn}>
          <Text style={s.notifyText}>NOTIFY ME ON DROP</Text>
        </TouchableOpacity>
      )}
    </ScrollView>
  );
}

const s = StyleSheet.create({
  root: { flex: 1, backgroundColor: colors.black },
  content: { padding: spacing.lg },
  hero: {
    height: 220, backgroundColor: colors.surface, borderRadius: 4,
    borderWidth: 1, borderColor: colors.border, justifyContent: 'flex-end',
    padding: spacing.md, marginBottom: spacing.md,
  },
  heroLabel: { color: colors.ridgeDim, fontSize: 9, ...fonts.heading },
  title: { color: colors.white, fontSize: 22, fontWeight: '800', letterSpacing: 2, textTransform: 'uppercase' },
  sub: { color: colors.muted, fontSize: 12, marginTop: 4, marginBottom: spacing.sm },
  row: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: spacing.md },
  status: { fontSize: 11, fontWeight: '800', letterSpacing: 1 },
  live: { color: colors.success },
  soon: { color: colors.ridgeDim },
  price: { color: colors.ridge, fontSize: 20, fontWeight: '800' },
  divider: { height: 1, backgroundColor: colors.border, marginVertical: spacing.md },
  descHead: { color: colors.muted, fontSize: 10, ...fonts.heading, marginBottom: spacing.sm },
  desc: { color: colors.white, ...fonts.body, marginBottom: spacing.lg },
  btn: {
    backgroundColor: colors.ridge, borderRadius: 4,
    padding: spacing.md + 4, alignItems: 'center',
  },
  btnText: { color: colors.black, fontWeight: '800', letterSpacing: 2, fontSize: 14 },
  notifyBtn: {
    borderWidth: 1, borderColor: colors.border, borderRadius: 4,
    padding: spacing.md + 4, alignItems: 'center',
  },
  notifyText: { color: colors.muted, ...fonts.heading, fontSize: 12 },
});
