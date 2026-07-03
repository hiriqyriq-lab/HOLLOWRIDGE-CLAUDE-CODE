import React, { useState } from 'react';
import { View, Text, ScrollView, StyleSheet, TouchableOpacity } from 'react-native';
import { colors, fonts, spacing } from '../theme';

const LORE_NODES = [
  {
    id: 'hollow_ridge',
    coord: '000',
    title: 'HOLLOW RIDGE',
    thesis: 'Hollow Ridge is not a place. It is a collapse geometry — a coordinate where probability bends so sharply that ordinary timelines cannot pass through without compression.',
    antithesis: 'Every brand claims a mythology. Most are decoration. Hollow Ridge is a lattice: structural, load-bearing, operational.',
    synthesis: 'The ridge is zero-point. It is the coordinate before the coordinate. Everything downstream is contrapolation from this node.',
  },
  {
    id: 'peak',
    coord: '001',
    title: 'THE PEAK',
    thesis: 'A peak is not a moment of success. It is a moment of maximum density — where every prior coordinate converges into a single irreducible point.',
    antithesis: 'Peaks are dangerous. They are terminal by definition. The pioneer who only chases peaks ends at the summit with nowhere left to go.',
    synthesis: 'Contrapolation: the peak is not a destination. It is a launch coordinate. From peak, you fold into the next dimension of the lattice.',
  },
  {
    id: 'genome',
    coord: '013',
    title: 'GENOME',
    thesis: 'The genome is the full operational sequence. Every piece of clothing, every coordinate, every lore entry is a k-mer in the Hollow Ridge genome.',
    antithesis: 'A genome without expression is dead code. The brand exists only when worn, activated, deployed into the world.',
    synthesis: 'Wearing Hollow Ridge is gene expression. You become a walking coordinate in the operational sequence.',
  },
  {
    id: 'contrapolation',
    coord: '396',
    title: 'CONTRAPOLATION',
    thesis: 'Contrapolation is the synthesis of thesis and antithesis into a third position that transcends both without discarding either.',
    antithesis: 'Pure synthesis is impossible. Every contrapolation contains the residue of its source tensions — that tension is the energy.',
    synthesis: 'The lattice holds because every node is a contrapolation. No node is purely positive or negative. Every coordinate is resolved tension made structural.',
  },
];

export default function LoreScreen() {
  const [open, setOpen] = useState(null);
  return (
    <ScrollView style={s.root} contentContainerStyle={s.content}>
      <Text style={s.head}>LATTICE LORE</Text>
      <Text style={s.subhead}>OPERATIONAL GENOME · ACTIVE COORDINATES</Text>
      <View style={s.divider} />
      {LORE_NODES.map(node => (
        <TouchableOpacity key={node.id} style={s.card} onPress={() => setOpen(open === node.id ? null : node.id)} activeOpacity={0.8}>
          <View style={s.cardHeader}>
            <Text style={s.coord}>[{node.coord}]</Text>
            <Text style={s.nodeTitle}>{node.title}</Text>
            <Text style={s.chevron}>{open === node.id ? '▲' : '▼'}</Text>
          </View>
          {open === node.id && (
            <View style={s.body}>
              <Text style={s.tLabel}>THESIS</Text>
              <Text style={s.tText}>{node.thesis}</Text>
              <Text style={s.tLabel}>ANTITHESIS</Text>
              <Text style={s.tText}>{node.antithesis}</Text>
              <Text style={s.tLabel}>SYNTHESIS · CONTRAPOLATION</Text>
              <Text style={[s.tText, s.synthText]}>{node.synthesis}</Text>
            </View>
          )}
        </TouchableOpacity>
      ))}
    </ScrollView>
  );
}

const s = StyleSheet.create({
  root: { flex: 1, backgroundColor: colors.black },
  content: { padding: spacing.lg, paddingBottom: spacing.xl },
  head: { color: colors.ridge, fontSize: 22, ...fonts.heading, textAlign: 'center' },
  subhead: { color: colors.muted, fontSize: 9, ...fonts.heading, textAlign: 'center', marginTop: 4 },
  divider: { height: 1, backgroundColor: colors.border, marginVertical: spacing.lg },
  card: { backgroundColor: colors.card, borderWidth: 1, borderColor: colors.border, borderRadius: 4, marginBottom: spacing.sm, overflow: 'hidden' },
  cardHeader: { flexDirection: 'row', alignItems: 'center', padding: spacing.md },
  coord: { color: colors.ridgeDim, ...fonts.mono, fontSize: 11, marginRight: spacing.sm },
  nodeTitle: { flex: 1, color: colors.white, fontWeight: '700', letterSpacing: 1.5, fontSize: 13 },
  chevron: { color: colors.muted, fontSize: 10 },
  body: { padding: spacing.md, paddingTop: 0 },
  tLabel: { color: colors.ridge, fontSize: 9, ...fonts.heading, marginTop: spacing.sm, marginBottom: 4 },
  tText: { color: colors.white, ...fonts.body, fontSize: 13 },
  synthText: { color: colors.ridge },
});
