import React, { useState, useRef } from 'react';
import {
  View, Text, TouchableOpacity, ScrollView,
  StyleSheet, TextInput, Animated, Pressable,
  StatusBar, Dimensions,
} from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { RootStackParamList } from '../navigation/types';
import Colors, { Spacing, Radius, Shadow } from '../constants/colors';

const { width: SCREEN_W } = Dimensions.get('window');

// ─── Language Toggle ──────────────────────────────────────────────────────────
type Lang = 'اردو' | 'Roman' | 'English';
const LANGUAGES: Lang[] = ['اردو', 'Roman', 'English'];

// ─── Legal Scenario Cards ─────────────────────────────────────────────────────
interface Scenario {
  key: string;
  emoji: string;
  title: { اردو: string; Roman: string; English: string };
  color: string;
  bg: string;
}

const SCENARIOS: Scenario[] = [
  {
    key: 'arrested',
    emoji: '🚔',
    title: { اردو: 'گرفتاری ہوئی', Roman: 'Giraftaar Ho Gaya', English: 'I Was Arrested' },
    color: Colors.DANGER,
    bg: Colors.DANGER_BG,
  },
  {
    key: 'salary',
    emoji: '💰',
    title: { اردو: 'تنخواہ نہیں ملی', Roman: 'Salary Nahi Mili', English: 'Salary Not Paid' },
    color: Colors.WARNING,
    bg: Colors.WARNING_BG,
  },
  {
    key: 'eviction',
    emoji: '🏠',
    title: { اردو: 'گھر سے نکالا', Roman: 'Ghar Se Nikala', English: 'Illegal Eviction' },
    color: '#7B4F9E',
    bg: '#F5EEF8',
  },
  {
    key: 'notice',
    emoji: '📋',
    title: { اردو: 'عدالتی نوٹس', Roman: 'Court Notice', English: 'Court Notice' },
    color: Colors.PRIMARY,
    bg: Colors.PRIMARY_SUBTLE,
  },
  {
    key: 'divorce',
    emoji: '💔',
    title: { اردو: 'طلاق / خلع', Roman: 'Talaq / Khula', English: 'Divorce / Khula' },
    color: '#C0392B',
    bg: '#FDF0EE',
  },
  {
    key: 'property',
    emoji: '🤝',
    title: { اردو: 'جائیداد تنازعہ', Roman: 'Property Jhagra', English: 'Property Dispute' },
    color: '#1A6B5A',
    bg: '#E8F5F2',
  },
];

// ─── Quick Action Pills ───────────────────────────────────────────────────────
const QUICK_ACTIONS = [
  { key: 'fir',  emoji: '🚨', label: { اردو: 'FIR', Roman: 'FIR', English: 'FIR' }, screen: 'FIRAnalyze' as keyof RootStackParamList },
  { key: 'doc',  emoji: '📄', label: { اردو: 'دستاویز', Roman: 'Document', English: 'Document' }, screen: 'DocAnalyze' as keyof RootStackParamList },
  { key: 'chat', emoji: '⚖️', label: { اردو: 'سوال', Roman: 'Sawal', English: 'Ask' }, screen: 'Chat' as keyof RootStackParamList },
];

export default function HomeScreen() {
  const navigation = useNavigation<NativeStackNavigationProp<RootStackParamList>>();
  const [lang, setLang] = useState<Lang>('اردو');
  const [query, setQuery] = useState('');
  const micScale = useRef(new Animated.Value(1)).current;

  const pulseMic = () => {
    Animated.sequence([
      Animated.spring(micScale, { toValue: 0.88, useNativeDriver: true, speed: 20 }),
      Animated.spring(micScale, { toValue: 1, useNativeDriver: true, speed: 20 }),
    ]).start();
  };

  const placeholders: Record<Lang, string> = {
    'اردو':    'اپنا قانونی سوال لکھیں...',
    'Roman':   'Apna legal sawal likhein...',
    'English': 'Ask your legal question...',
  };

  const greetings: Record<Lang, string> = {
    'اردو':    'السلام علیکم',
    'Roman':   'Assalam u Alaikum',
    'English': 'Welcome',
  };

  const subtitles: Record<Lang, string> = {
    'اردو':    'آپ کا مفت وکیل',
    'Roman':   'Aapka muft wakeel',
    'English': 'Your free legal guide',
  };

  const sectionTitles: Record<Lang, string> = {
    'اردو':    'آپ کی صورتحال کیا ہے؟',
    'Roman':   'Aapki sorat-e-hal kya hai?',
    'English': 'What is your situation?',
  };

  return (
    <View style={styles.root}>
      <StatusBar barStyle="light-content" backgroundColor={Colors.PRIMARY} />

      {/* ── Fixed Header ─────────────────────────────────────────────────── */}
      <View style={styles.header}>
        {/* Greeting */}
        <View style={styles.headerLeft}>
          <Text style={styles.greeting}>{greetings[lang]} 🌿</Text>
          <Text style={styles.subtitle}>{subtitles[lang]}</Text>
        </View>

        {/* Language Toggle */}
        <View style={styles.langToggle}>
          {LANGUAGES.map(l => (
            <TouchableOpacity
              key={l}
              style={[styles.langBtn, lang === l && styles.langBtnActive]}
              onPress={() => setLang(l)}
              activeOpacity={0.7}
            >
              <Text style={[styles.langBtnText, lang === l && styles.langBtnTextActive]}>
                {l}
              </Text>
            </TouchableOpacity>
          ))}
        </View>
      </View>

      <ScrollView
        style={styles.scroll}
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
      >
        {/* ── Hero Search Bar ───────────────────────────────────────────── */}
        <View style={styles.searchCard}>
          <View style={styles.searchRow}>
            <TextInput
              style={styles.searchInput}
              value={query}
              onChangeText={setQuery}
              placeholder={placeholders[lang]}
              placeholderTextColor={Colors.TEXT_MUTED}
              returnKeyType="search"
              onSubmitEditing={() => query.trim() && navigation.navigate('Chat')}
            />
            {/* Mic button — large, prominent, crucial for semi-literate users */}
            <Animated.View style={{ transform: [{ scale: micScale }] }}>
              <TouchableOpacity
                style={styles.micBtn}
                onPress={pulseMic}
                activeOpacity={0.85}
              >
                <Text style={styles.micIcon}>🎙️</Text>
              </TouchableOpacity>
            </Animated.View>
          </View>

          {/* Quick action pills below search */}
          <View style={styles.pillsRow}>
            {QUICK_ACTIONS.map(a => (
              <TouchableOpacity
                key={a.key}
                style={styles.pill}
                onPress={() => navigation.navigate(a.screen as any)}
                activeOpacity={0.75}
              >
                <Text style={styles.pillEmoji}>{a.emoji}</Text>
                <Text style={styles.pillText}>{a.label[lang]}</Text>
              </TouchableOpacity>
            ))}
          </View>
        </View>

        {/* ── Scenario Section Title ────────────────────────────────────── */}
        <Text style={styles.sectionTitle}>{sectionTitles[lang]}</Text>

        {/* ── Scenario Cards Grid ───────────────────────────────────────── */}
        <View style={styles.grid}>
          {SCENARIOS.map((s, i) => (
            <ScenarioCard
              key={s.key}
              scenario={s}
              lang={lang}
              onPress={() => navigation.navigate('Rights', { scenarioKey: s.key })}
              index={i}
            />
          ))}
        </View>

        {/* ── Disclaimer ───────────────────────────────────────────────── */}
        <View style={styles.disclaimer}>
          <Text style={styles.disclaimerText}>
            {lang === 'اردو'
              ? '⚠️ وکیل رہنمائی دیتا ہے — یہ پیشہ ورانہ قانونی مشورہ نہیں ہے'
              : lang === 'Roman'
              ? '⚠️ Wakeel guidance deta hai — professional legal advice nahi'
              : '⚠️ Wakeel provides guidance — not professional legal advice'}
          </Text>
        </View>
      </ScrollView>
    </View>
  );
}

// ─── Scenario Card Component ──────────────────────────────────────────────────
function ScenarioCard({
  scenario, lang, onPress, index,
}: {
  scenario: Scenario;
  lang: Lang;
  onPress: () => void;
  index: number;
}) {
  const scale = useRef(new Animated.Value(1)).current;

  const onPressIn = () =>
    Animated.spring(scale, { toValue: 0.95, useNativeDriver: true, speed: 30 }).start();
  const onPressOut = () =>
    Animated.spring(scale, { toValue: 1, useNativeDriver: true, speed: 30 }).start();

  return (
    <Animated.View style={[styles.cardWrap, { transform: [{ scale }] }]}>
      <Pressable
        style={[styles.card, { backgroundColor: scenario.bg }]}
        onPress={onPress}
        onPressIn={onPressIn}
        onPressOut={onPressOut}
      >
        {/* Colored top strip */}
        <View style={[styles.cardStrip, { backgroundColor: scenario.color }]} />
        <View style={styles.cardContent}>
          <Text style={styles.cardEmoji}>{scenario.emoji}</Text>
          <Text style={[styles.cardTitle, { color: scenario.color }]} numberOfLines={2}>
            {scenario.title[lang]}
          </Text>
          <View style={[styles.cardArrow, { backgroundColor: scenario.color + '20' }]}>
            <Text style={[styles.cardArrowText, { color: scenario.color }]}>←</Text>
          </View>
        </View>
      </Pressable>
    </Animated.View>
  );
}

// ─── Styles ───────────────────────────────────────────────────────────────────
const CARD_W = (SCREEN_W - Spacing.MD * 2 - Spacing.SM) / 2;

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: Colors.BACKGROUND },

  // Header
  header: {
    backgroundColor: Colors.PRIMARY,
    paddingTop: 52,
    paddingBottom: 20,
    paddingHorizontal: Spacing.MD,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-end',
    borderBottomLeftRadius: Radius.XL,
    borderBottomRightRadius: Radius.XL,
    ...Shadow.LG,
  },
  headerLeft: { flex: 1 },
  greeting: { fontSize: 20, fontWeight: '800', color: Colors.TEXT_ON_GREEN, marginBottom: 2 },
  subtitle: { fontSize: 13, color: 'rgba(255,255,255,0.7)' },

  // Language toggle
  langToggle: {
    flexDirection: 'row',
    backgroundColor: 'rgba(255,255,255,0.12)',
    borderRadius: Radius.FULL,
    padding: 3,
    gap: 2,
  },
  langBtn: {
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: Radius.FULL,
  },
  langBtnActive: {
    backgroundColor: Colors.TEXT_ON_GREEN,
  },
  langBtnText: {
    fontSize: 11,
    fontWeight: '600',
    color: 'rgba(255,255,255,0.7)',
  },
  langBtnTextActive: {
    color: Colors.PRIMARY,
  },

  scroll: { flex: 1 },
  scrollContent: { padding: Spacing.MD, paddingBottom: 40 },

  // Search card
  searchCard: {
    backgroundColor: Colors.SURFACE,
    borderRadius: Radius.LG,
    padding: Spacing.MD,
    marginBottom: Spacing.LG,
    ...Shadow.MD,
  },
  searchRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.SM,
    marginBottom: Spacing.MD,
  },
  searchInput: {
    flex: 1,
    backgroundColor: Colors.SURFACE_2,
    borderRadius: Radius.FULL,
    paddingHorizontal: Spacing.MD,
    paddingVertical: 13,
    fontSize: 15,
    color: Colors.TEXT_PRIMARY,
    borderWidth: 1.5,
    borderColor: Colors.BORDER,
  },
  micBtn: {
    width: 52,
    height: 52,
    borderRadius: 26,
    backgroundColor: Colors.PRIMARY,
    justifyContent: 'center',
    alignItems: 'center',
    ...Shadow.LG,
  },
  micIcon: { fontSize: 22 },

  // Pills
  pillsRow: {
    flexDirection: 'row',
    gap: Spacing.SM,
  },
  pill: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: Colors.PRIMARY_SUBTLE,
    borderRadius: Radius.FULL,
    paddingVertical: 9,
    paddingHorizontal: Spacing.SM,
    gap: 5,
    borderWidth: 1.5,
    borderColor: Colors.PRIMARY + '30',
  },
  pillEmoji: { fontSize: 15 },
  pillText: { fontSize: 13, fontWeight: '700', color: Colors.PRIMARY },

  // Section title
  sectionTitle: {
    fontSize: 17,
    fontWeight: '800',
    color: Colors.TEXT_PRIMARY,
    marginBottom: Spacing.MD,
    marginLeft: 2,
  },

  // Scenario grid
  grid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.SM,
    marginBottom: Spacing.LG,
  },
  cardWrap: { width: CARD_W },
  card: {
    width: '100%',
    borderRadius: Radius.LG,
    overflow: 'hidden',
    ...Shadow.SM,
  },
  cardStrip: { height: 4, width: '100%' },
  cardContent: { padding: Spacing.MD, minHeight: 110 },
  cardEmoji: { fontSize: 32, marginBottom: Spacing.SM },
  cardTitle: {
    fontSize: 14,
    fontWeight: '700',
    lineHeight: 20,
    marginBottom: Spacing.SM,
    flex: 1,
  },
  cardArrow: {
    alignSelf: 'flex-end',
    width: 28,
    height: 28,
    borderRadius: 14,
    justifyContent: 'center',
    alignItems: 'center',
  },
  cardArrowText: { fontSize: 16, fontWeight: 'bold' },

  // Disclaimer
  disclaimer: {
    backgroundColor: Colors.YELLOW_BG,
    borderRadius: Radius.MD,
    padding: Spacing.MD,
    borderLeftWidth: 3,
    borderLeftColor: Colors.WARNING,
  },
  disclaimerText: { fontSize: 12, color: Colors.TEXT_SECONDARY, lineHeight: 18 },
});
