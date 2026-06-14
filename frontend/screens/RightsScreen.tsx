import React, { useState } from 'react';
import {
  View, Text, TouchableOpacity, ScrollView,
  StyleSheet, Animated,
} from 'react-native';
import Colors from '../constants/colors';

type ScenarioKey = 'arrested' | 'divorce' | 'eviction' | 'salary' | 'notice' | 'property';

interface FlowNode {
  id: string;
  question: string;
  questionRoman: string;
  yes?: string;         // next node id or 'result:...'
  no?: string;
  result?: string;      // shown when this is a leaf
  citation?: string;
}

// Arrested flowchart (hardcoded as per prompt 14)
const ARRESTED_FLOW: Record<string, FlowNode> = {
  q1: {
    id: 'q1',
    question: 'کیا پولیس کے پاس وارنٹ تھا؟',
    questionRoman: 'Kya police ke paas warrant tha?',
    yes: 'q2a',
    no: 'q2b',
  },
  q2a: {
    id: 'q2a',
    question: 'کیا آپ نے وارنٹ پڑھا / دیکھا؟',
    questionRoman: "Kya aap ne warrant parha / dekha?",
    yes: 'q3',
    no: 'result:r_warrant',
  },
  q2b: {
    id: 'q2b',
    question: 'کیا یہ قابل گرفتاری جرم تھا؟',
    questionRoman: 'Kya yeh cognizable offence tha?',
    yes: 'q3',
    no: 'result:r_nowarrant',
  },
  q3: {
    id: 'q3',
    question: 'کیا آپ کو گرفتاری کی وجہ بتائی گئی؟',
    questionRoman: 'Kya aap ko giraftaari ki wajah batayi gayi?',
    yes: 'q4',
    no: 'result:r_reason',
  },
  q4: {
    id: 'q4',
    question: 'کیا آپ کو وکیل کا حق بتایا گیا؟',
    questionRoman: 'Kya aap ko vakeel ka haq bataya gaya?',
    yes: 'q5',
    no: 'result:r_lawyer',
  },
  q5: {
    id: 'q5',
    question: 'کیا آپ کو 24 گھنٹے میں مجسٹریٹ کے سامنے پیش کیا گیا؟',
    questionRoman: '24 ghante mein magistrate ke saamne paish kiya gaya?',
    yes: 'result:r_ok',
    no: 'result:r_24hrs',
  },
};

const RESULTS: Record<string, { text: string; citation: string }> = {
  r_warrant: { text: 'آپ کو وارنٹ دیکھنے کا حق ہے۔ پولیس وارنٹ دکھانے سے انکار نہیں کر سکتی۔', citation: 'ضابطہ فوجداری دفعہ 75' },
  r_nowarrant: { text: 'بغیر وارنٹ اور بغیر قابل گرفتاری جرم کے گرفتاری غیر قانونی ہے۔ آپ رہا ہونے کے حقدار ہیں۔', citation: 'آئین آرٹیکل 9' },
  r_reason: { text: 'گرفتاری کی وجہ بتانا قانوناً ضروری ہے۔ یہ آپ کا بنیادی حق ہے۔', citation: 'ضابطہ فوجداری دفعہ 50' },
  r_lawyer: { text: 'آپ کو فوری طور پر وکیل سے ملنے کا حق ہے۔ پولیس اس حق سے انکار نہیں کر سکتی۔', citation: 'آئین آرٹیکل 10' },
  r_24hrs: { text: '24 گھنٹے میں مجسٹریٹ کے سامنے پیش نہ کرنا آئینی خلاف ورزی ہے۔ یہ ہیبیس کارپس کی بنیاد ہے۔', citation: 'آئین آرٹیکل 10(2)' },
  r_ok: { text: 'آپ کی گرفتاری ظاہری طور پر قانونی طریقے سے کی گئی۔ پھر بھی وکیل سے مشورہ کریں۔', citation: 'ضابطہ فوجداری' },
};

const SCENARIOS = [
  { key: 'arrested' as ScenarioKey, emoji: '🚔', title: 'گرفتاری', roman: 'Police ne pakad liya' },
  { key: 'divorce' as ScenarioKey, emoji: '💔', title: 'طلاق / خلع', roman: 'Rishta khatam karna hai' },
  { key: 'eviction' as ScenarioKey, emoji: '🏠', title: 'بے دخلی', roman: 'Ghar se nikala ja raha hun' },
  { key: 'salary' as ScenarioKey, emoji: '💰', title: 'تنخواہ نہ ملنا', roman: 'Salary nahi mili' },
  { key: 'notice' as ScenarioKey, emoji: '📋', title: 'عدالتی نوٹس', roman: 'Court ka notice mila' },
  { key: 'property' as ScenarioKey, emoji: '🤝', title: 'جائیداد تنازعہ', roman: 'Property ka masla hai' },
];

export default function RightsScreen() {
  const [selectedScenario, setSelectedScenario] = useState<ScenarioKey | null>(null);
  const [currentNodeId, setCurrentNodeId] = useState<string>('q1');
  const [answersPath, setAnswersPath] = useState<string[]>([]);
  const [resultKey, setResultKey] = useState<string | null>(null);

  const selectScenario = (key: ScenarioKey) => {
    setSelectedScenario(key);
    setCurrentNodeId('q1');
    setAnswersPath([]);
    setResultKey(null);
  };

  const answer = (choice: 'yes' | 'no') => {
    if (selectedScenario !== 'arrested') return;
    const node = ARRESTED_FLOW[currentNodeId];
    const next = choice === 'yes' ? node.yes : node.no;
    setAnswersPath(prev => [...prev, choice]);
    if (!next) return;
    if (next.startsWith('result:')) {
      setResultKey(next.replace('result:', ''));
    } else {
      setCurrentNodeId(next);
    }
  };

  const reset = () => {
    setSelectedScenario(null);
    setCurrentNodeId('q1');
    setAnswersPath([]);
    setResultKey(null);
  };

  const totalQuestions = Object.keys(ARRESTED_FLOW).length;
  const currentStep = answersPath.length + 1;

  // ── Scenario selection ────────────────────────────────────────────────────
  if (!selectedScenario) {
    return (
      <ScrollView style={styles.container} contentContainerStyle={styles.content}>
        <View style={styles.header}>
          <Text style={styles.headerTitle}>🛡️ اپنے حقوق جانیں</Text>
          <Text style={styles.headerSub}>اپنی صورتحال منتخب کریں</Text>
        </View>
        <View style={styles.grid}>
          {SCENARIOS.map(s => (
            <TouchableOpacity
              key={s.key}
              style={styles.scenarioCard}
              onPress={() => selectScenario(s.key)}
            >
              <Text style={styles.scenarioEmoji}>{s.emoji}</Text>
              <Text style={styles.scenarioTitle}>{s.title}</Text>
              <Text style={styles.scenarioRoman}>{s.roman}</Text>
              {s.key !== 'arrested' && (
                <View style={styles.comingSoonBadge}>
                  <Text style={styles.comingSoonText}>جلد آ رہا ہے</Text>
                </View>
              )}
            </TouchableOpacity>
          ))}
        </View>
      </ScrollView>
    );
  }

  // ── Coming soon for non-arrested scenarios ────────────────────────────────
  if (selectedScenario !== 'arrested') {
    return (
      <View style={styles.container}>
        <View style={styles.comingSoonContainer}>
          <Text style={styles.comingSoonEmoji}>🚧</Text>
          <Text style={styles.comingSoonTitle}>جلد آ رہا ہے</Text>
          <Text style={styles.comingSoonDesc}>یہ سیکشن تیار ہو رہا ہے</Text>
          <TouchableOpacity style={styles.backBtn} onPress={reset}>
            <Text style={styles.backBtnText}>واپس جائیں</Text>
          </TouchableOpacity>
        </View>
      </View>
    );
  }

  // ── Result ────────────────────────────────────────────────────────────────
  if (resultKey && RESULTS[resultKey]) {
    const res = RESULTS[resultKey];
    return (
      <ScrollView style={styles.container} contentContainerStyle={styles.content}>
        <View style={styles.resultHeader}>
          <Text style={styles.resultEmoji}>📌</Text>
          <Text style={styles.resultTitle}>آپ کا حق</Text>
        </View>
        <View style={styles.resultCard}>
          <Text style={styles.resultText}>{res.text}</Text>
          <View style={styles.citationPill}>
            <Text style={styles.citationText}>{res.citation}</Text>
          </View>
        </View>
        <View style={styles.pathSummary}>
          <Text style={styles.pathLabel}>آپ کے جوابات: {answersPath.map(a => a === 'yes' ? 'ہاں' : 'نہیں').join(' → ')}</Text>
        </View>
        <TouchableOpacity style={styles.resetBtn} onPress={reset}>
          <Text style={styles.resetBtnText}>دوبارہ شروع کریں</Text>
        </TouchableOpacity>
      </ScrollView>
    );
  }

  // ── Question flow ─────────────────────────────────────────────────────────
  const node = ARRESTED_FLOW[currentNodeId];
  const progress = ((currentStep - 1) / totalQuestions) * 100;

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      {/* Header */}
      <View style={styles.flowHeader}>
        <Text style={styles.flowTitle}>🚔 گرفتاری</Text>
        <TouchableOpacity onPress={reset}>
          <Text style={styles.exitText}>✕ باہر</Text>
        </TouchableOpacity>
      </View>

      {/* Progress bar */}
      <View style={styles.progressBar}>
        <View style={[styles.progressFill, { width: `${progress}%` }]} />
      </View>
      <Text style={styles.progressLabel}>مرحلہ {currentStep} از {totalQuestions}</Text>

      {/* Question card */}
      <View style={styles.questionCard}>
        <Text style={styles.questionText}>{node.question}</Text>
        <Text style={styles.questionRoman}>{node.questionRoman}</Text>
      </View>

      {/* Answer buttons */}
      <TouchableOpacity style={styles.yesBtn} onPress={() => answer('yes')}>
        <Text style={styles.yesBtnText}>ہاں (Yes)</Text>
      </TouchableOpacity>
      <TouchableOpacity style={styles.noBtn} onPress={() => answer('no')}>
        <Text style={styles.noBtnText}>نہیں (No)</Text>
      </TouchableOpacity>
      <TouchableOpacity style={styles.dontKnowBtn} onPress={() => answer('no')}>
        <Text style={styles.dontKnowText}>مجھے معلوم نہیں (I don't know)</Text>
      </TouchableOpacity>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.BACKGROUND },
  content: { padding: 20, paddingBottom: 40 },
  header: { backgroundColor: Colors.PRIMARY, borderRadius: 16, padding: 20, marginBottom: 20, alignItems: 'center' },
  headerTitle: { fontSize: 22, fontWeight: 'bold', color: Colors.SECONDARY },
  headerSub: { fontSize: 13, color: '#ffffff99', marginTop: 4 },
  grid: { flexDirection: 'row', flexWrap: 'wrap', gap: 14 },
  scenarioCard: { width: '47%', backgroundColor: Colors.SURFACE, borderRadius: 14, padding: 16, alignItems: 'center', elevation: 3, shadowColor: '#000', shadowOpacity: 0.07, shadowRadius: 5, shadowOffset: { width: 0, height: 2 } },
  scenarioEmoji: { fontSize: 36, marginBottom: 8 },
  scenarioTitle: { fontSize: 15, fontWeight: '700', color: Colors.TEXT_DARK, textAlign: 'center', marginBottom: 4 },
  scenarioRoman: { fontSize: 11, color: Colors.GRAY, textAlign: 'center' },
  comingSoonBadge: { marginTop: 8, backgroundColor: Colors.GRAY_LIGHT, paddingHorizontal: 8, paddingVertical: 3, borderRadius: 10 },
  comingSoonText: { fontSize: 10, color: Colors.GRAY },
  comingSoonContainer: { flex: 1, justifyContent: 'center', alignItems: 'center', padding: 40 },
  comingSoonEmoji: { fontSize: 60, marginBottom: 16 },
  comingSoonTitle: { fontSize: 22, fontWeight: 'bold', color: Colors.TEXT_DARK, marginBottom: 8 },
  comingSoonDesc: { fontSize: 14, color: Colors.GRAY, marginBottom: 24 },
  backBtn: { backgroundColor: Colors.PRIMARY, paddingHorizontal: 24, paddingVertical: 12, borderRadius: 10 },
  backBtnText: { color: '#fff', fontWeight: '600' },
  flowHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 },
  flowTitle: { fontSize: 20, fontWeight: 'bold', color: Colors.PRIMARY },
  exitText: { fontSize: 14, color: Colors.GRAY },
  progressBar: { height: 6, backgroundColor: Colors.GRAY_LIGHT, borderRadius: 3, marginBottom: 6 },
  progressFill: { height: 6, backgroundColor: Colors.PRIMARY, borderRadius: 3 },
  progressLabel: { fontSize: 12, color: Colors.GRAY, marginBottom: 20, textAlign: 'right' },
  questionCard: { backgroundColor: Colors.SURFACE, borderRadius: 16, padding: 24, marginBottom: 24, elevation: 3, shadowColor: '#000', shadowOpacity: 0.07, shadowRadius: 6, shadowOffset: { width: 0, height: 3 } },
  questionText: { fontSize: 20, fontWeight: '700', color: Colors.TEXT_DARK, lineHeight: 30, marginBottom: 12, textAlign: 'right' },
  questionRoman: { fontSize: 14, color: Colors.GRAY, fontStyle: 'italic' },
  yesBtn: { backgroundColor: Colors.SUCCESS, padding: 16, borderRadius: 12, alignItems: 'center', marginBottom: 12 },
  yesBtnText: { color: '#fff', fontSize: 18, fontWeight: '700' },
  noBtn: { borderWidth: 2, borderColor: Colors.ACCENT_RED, padding: 15, borderRadius: 12, alignItems: 'center', marginBottom: 12 },
  noBtnText: { color: Colors.ACCENT_RED, fontSize: 18, fontWeight: '700' },
  dontKnowBtn: { padding: 12, alignItems: 'center' },
  dontKnowText: { color: Colors.GRAY, fontSize: 14 },
  resultHeader: { alignItems: 'center', marginBottom: 20 },
  resultEmoji: { fontSize: 50, marginBottom: 8 },
  resultTitle: { fontSize: 22, fontWeight: 'bold', color: Colors.PRIMARY },
  resultCard: { backgroundColor: Colors.SURFACE, borderRadius: 16, padding: 20, marginBottom: 16, borderWidth: 2, borderColor: Colors.PRIMARY, elevation: 3, shadowColor: '#000', shadowOpacity: 0.07, shadowRadius: 6, shadowOffset: { width: 0, height: 3 } },
  resultText: { fontSize: 17, color: Colors.TEXT_DARK, lineHeight: 26, marginBottom: 16, textAlign: 'right' },
  citationPill: { backgroundColor: Colors.PRIMARY, paddingHorizontal: 14, paddingVertical: 6, borderRadius: 20, alignSelf: 'flex-start' },
  citationText: { color: '#fff', fontSize: 13, fontWeight: '600' },
  pathSummary: { backgroundColor: Colors.GRAY_LIGHT, borderRadius: 10, padding: 12, marginBottom: 20 },
  pathLabel: { fontSize: 12, color: Colors.GRAY, textAlign: 'center' },
  resetBtn: { backgroundColor: Colors.SECONDARY, padding: 14, borderRadius: 12, alignItems: 'center' },
  resetBtnText: { color: Colors.TEXT_DARK, fontSize: 16, fontWeight: '700' },
});
