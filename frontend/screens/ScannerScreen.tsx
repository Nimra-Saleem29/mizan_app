import React from 'react';
import {
  View, Text, TouchableOpacity, StyleSheet, ScrollView,
} from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { RootStackParamList } from '../navigation/types';
import Colors, { Spacing, Radius, Shadow } from '../constants/colors';

const SCAN_OPTIONS = [
  {
    key: 'fir',
    emoji: '🚨',
    title: 'FIR تجزیہ',
    titleRoman: 'FIR Tahleel',
    desc: 'FIR کی تصویر اپلوڈ کریں اور دفعات سمجھیں',
    descEn: 'Upload FIR photo, understand sections',
    color: Colors.DANGER,
    bg: Colors.DANGER_BG,
    screen: 'FIRAnalyze' as keyof RootStackParamList,
  },
  {
    key: 'doc',
    emoji: '📄',
    title: 'دستاویز تجزیہ',
    titleRoman: 'Document Tahleel',
    desc: 'کوئی بھی قانونی کاغذ سکین کریں',
    descEn: 'Scan any legal document for risks',
    color: Colors.PRIMARY,
    bg: Colors.PRIMARY_SUBTLE,
    screen: 'DocAnalyze' as keyof RootStackParamList,
  },
];

export default function ScannerScreen() {
  const navigation = useNavigation<NativeStackNavigationProp<RootStackParamList>>();

  return (
    <View style={styles.root}>
      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.headerTitle}>📷 سکینر</Text>
        <Text style={styles.headerSub}>Scanner</Text>
      </View>

      <ScrollView contentContainerStyle={styles.content}>
        <Text style={styles.instruction}>
          کون سی چیز سکین کرنی ہے؟{'\n'}
          <Text style={styles.instructionSub}>What would you like to scan?</Text>
        </Text>

        {SCAN_OPTIONS.map(opt => (
          <TouchableOpacity
            key={opt.key}
            style={[styles.card, { backgroundColor: opt.bg, borderLeftColor: opt.color }]}
            onPress={() => navigation.navigate(opt.screen as any)}
            activeOpacity={0.82}
          >
            <View style={[styles.iconCircle, { backgroundColor: opt.color }]}>
              <Text style={styles.iconEmoji}>{opt.emoji}</Text>
            </View>
            <View style={styles.cardText}>
              <Text style={[styles.cardTitle, { color: opt.color }]}>{opt.title}</Text>
              <Text style={styles.cardRoman}>{opt.titleRoman}</Text>
              <Text style={styles.cardDesc}>{opt.desc}</Text>
              <Text style={styles.cardDescEn}>{opt.descEn}</Text>
            </View>
            <Text style={[styles.arrow, { color: opt.color }]}>›</Text>
          </TouchableOpacity>
        ))}

        {/* Tip */}
        <View style={styles.tipBox}>
          <Text style={styles.tipEmoji}>💡</Text>
          <Text style={styles.tipText}>
            بہترین نتیجے کے لیے روشنی میں واضح تصویر لیں{'\n'}
            <Text style={styles.tipTextEn}>Take a clear photo in good lighting</Text>
          </Text>
        </View>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: Colors.BACKGROUND },
  header: {
    backgroundColor: Colors.PRIMARY,
    paddingTop: 54,
    paddingBottom: 20,
    paddingHorizontal: Spacing.MD,
    borderBottomLeftRadius: 24,
    borderBottomRightRadius: 24,
    ...Shadow.LG,
  },
  headerTitle: { fontSize: 24, fontWeight: '800', color: Colors.TEXT_ON_GREEN },
  headerSub: { fontSize: 13, color: 'rgba(255,255,255,0.6)', marginTop: 2 },
  content: { padding: Spacing.MD, paddingBottom: 40 },
  instruction: {
    fontSize: 18, fontWeight: '700', color: Colors.TEXT_PRIMARY,
    marginBottom: Spacing.LG, marginTop: Spacing.SM, lineHeight: 28,
  },
  instructionSub: { fontSize: 14, color: Colors.TEXT_MUTED, fontWeight: '400' },
  card: {
    flexDirection: 'row',
    alignItems: 'center',
    borderRadius: Radius.LG,
    padding: Spacing.MD,
    marginBottom: Spacing.MD,
    borderLeftWidth: 5,
    gap: Spacing.MD,
    ...Shadow.SM,
  },
  iconCircle: {
    width: 60,
    height: 60,
    borderRadius: 30,
    justifyContent: 'center',
    alignItems: 'center',
  },
  iconEmoji: { fontSize: 28 },
  cardText: { flex: 1 },
  cardTitle: { fontSize: 18, fontWeight: '800', marginBottom: 2 },
  cardRoman: { fontSize: 12, color: Colors.TEXT_MUTED, marginBottom: 4 },
  cardDesc: { fontSize: 13, color: Colors.TEXT_SECONDARY, lineHeight: 18 },
  cardDescEn: { fontSize: 11, color: Colors.TEXT_MUTED, marginTop: 2 },
  arrow: { fontSize: 28, fontWeight: '300' },
  tipBox: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    backgroundColor: Colors.YELLOW_BG,
    borderRadius: Radius.MD,
    padding: Spacing.MD,
    gap: Spacing.SM,
    marginTop: Spacing.SM,
    borderWidth: 1,
    borderColor: Colors.YELLOW_SOFT,
  },
  tipEmoji: { fontSize: 20 },
  tipText: { flex: 1, fontSize: 13, color: Colors.TEXT_SECONDARY, lineHeight: 20 },
  tipTextEn: { fontSize: 11, color: Colors.TEXT_MUTED },
});
