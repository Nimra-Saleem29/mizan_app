import React, { useState } from 'react';
import {
  View, Text, TouchableOpacity, ScrollView,
  StyleSheet, ActivityIndicator, Image,
} from 'react-native';
import * as ImagePicker from 'expo-image-picker';
import { analyzeDocument, DocumentAnalysisResponse, RiskFlag } from '../utils/api';
import Colors from '../constants/colors';

type Step = 'input' | 'loading' | 'result';

const DOC_TYPES: Record<string, string> = {
  rent_agreement: 'کرایہ نامہ',
  employment_contract: 'ملازمت',
  court_notice: 'عدالتی نوٹس',
  property_deed: 'جائیداد',
  loan_agreement: 'قرضہ',
  eviction_notice: 'بے دخلی',
  general_legal_document: 'قانونی دستاویز',
};

const RISK_COLORS: Record<string, string> = {
  HIGH: Colors.ACCENT_RED,
  MEDIUM: Colors.WARNING,
  LOW: Colors.SUCCESS,
};

const RISK_EMOJI: Record<string, string> = {
  HIGH: '🔴',
  MEDIUM: '🟡',
  LOW: '🟢',
};

export default function DocumentScreen() {
  const [step, setStep] = useState<Step>('input');
  const [imageUri, setImageUri] = useState<string | null>(null);
  const [result, setResult] = useState<DocumentAnalysisResponse | null>(null);
  const [error, setError] = useState('');
  const [expandedFlag, setExpandedFlag] = useState<number | null>(null);

  const pickImage = async () => {
    const perm = await ImagePicker.requestCameraPermissionsAsync();
    if (!perm.granted) return;
    const res = await ImagePicker.launchCameraAsync({ quality: 0.9 });
    if (!res.canceled) setImageUri(res.assets[0].uri);
  };

  const pickFromGallery = async () => {
    const res = await ImagePicker.launchImageLibraryAsync({ quality: 0.9 });
    if (!res.canceled) setImageUri(res.assets[0].uri);
  };

  const analyze = async () => {
    if (!imageUri) return;
    setError('');
    setStep('loading');
    try {
      const data = await analyzeDocument(imageUri);
      setResult(data);
      setStep('result');
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? 'تجزیہ نہیں ہو سکا۔ دوبارہ کوشش کریں۔');
      setStep('input');
    }
  };

  const reset = () => {
    setStep('input');
    setResult(null);
    setImageUri(null);
    setError('');
    setExpandedFlag(null);
  };

  // ── Loading ──────────────────────────────────────────────────────────────
  if (step === 'loading') {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color={Colors.PRIMARY} />
        <Text style={styles.loadingText}>دستاویز کا تجزیہ ہو رہا ہے...</Text>
        <Text style={styles.loadingSubText}>(Analyzing document...)</Text>
      </View>
    );
  }

  // ── Result ───────────────────────────────────────────────────────────────
  if (step === 'result' && result) {
    const urduType = DOC_TYPES[result.document_type] ?? result.document_type;
    const highRisks = result.risk_flags.filter(f => f.risk_level === 'HIGH');

    return (
      <ScrollView style={styles.container} contentContainerStyle={styles.content}>
        {/* Doc type badge */}
        <View style={styles.typeBadgeRow}>
          <View style={styles.typeBadge}>
            <Text style={styles.typeBadgeText}>📋 {urduType}</Text>
          </View>
          {highRisks.length > 0 && (
            <View style={styles.dangerBadge}>
              <Text style={styles.dangerBadgeText}>⚠️ {highRisks.length} خطرناک شقیں</Text>
            </View>
          )}
        </View>

        {/* Summary */}
        <View style={styles.summaryCard}>
          <Text style={styles.summaryLabel}>📝 خلاصہ</Text>
          <Text style={styles.summaryText}>{result.plain_explanation}</Text>
        </View>

        {/* Risk Flags */}
        {result.risk_flags.length > 0 && (
          <>
            <Text style={styles.sectionHeading}>⚠️ خطرے کی نشانیاں</Text>
            {result.risk_flags.map((flag: RiskFlag, i: number) => (
              <TouchableOpacity
                key={i}
                style={[styles.flagCard, { borderLeftColor: RISK_COLORS[flag.risk_level] }]}
                onPress={() => setExpandedFlag(expandedFlag === i ? null : i)}
                activeOpacity={0.8}
              >
                <View style={styles.flagHeader}>
                  <Text style={styles.flagEmoji}>{RISK_EMOJI[flag.risk_level]}</Text>
                  <View style={[styles.riskPill, { backgroundColor: RISK_COLORS[flag.risk_level] }]}>
                    <Text style={styles.riskPillText}>{flag.risk_level}</Text>
                  </View>
                  <Text style={styles.flagClause} numberOfLines={expandedFlag === i ? undefined : 1}>
                    {flag.clause_text}
                  </Text>
                </View>
                {expandedFlag === i && (
                  <View style={styles.flagDetail}>
                    <Text style={styles.flagExplanation}>{flag.explanation}</Text>
                  </View>
                )}
                <Text style={styles.expandHint}>{expandedFlag === i ? '▲ کم کریں' : '▼ تفصیل'}</Text>
              </TouchableOpacity>
            ))}
          </>
        )}

        {/* No risks */}
        {result.risk_flags.length === 0 && (
          <View style={styles.safeBox}>
            <Text style={styles.safeText}>✅ کوئی خطرناک شق نہیں ملی۔ دستاویز محفوظ لگتی ہے۔</Text>
          </View>
        )}

        <TouchableOpacity style={styles.resetBtn} onPress={reset}>
          <Text style={styles.resetBtnText}>نئی دستاویز</Text>
        </TouchableOpacity>
      </ScrollView>
    );
  }

  // ── Input ─────────────────────────────────────────────────────────────────
  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>📄 دستاویز تجزیہ</Text>
        <Text style={styles.headerSub}>کوئی بھی قانونی کاغذ سکین کریں</Text>
      </View>

      {/* Doc type chips */}
      <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.chipsRow}>
        {Object.values(DOC_TYPES).map((label, i) => (
          <View key={i} style={styles.chip}>
            <Text style={styles.chipText}>{label}</Text>
          </View>
        ))}
      </ScrollView>

      {/* Upload area */}
      <View style={styles.uploadArea}>
        {imageUri ? (
          <Image source={{ uri: imageUri }} style={styles.previewImage} />
        ) : (
          <>
            <Text style={styles.uploadIcon}>📤</Text>
            <Text style={styles.uploadText}>تصویر کھینچیں یا فائل اپلوڈ کریں</Text>
          </>
        )}
        <View style={styles.uploadButtonRow}>
          <TouchableOpacity style={styles.uploadBtn} onPress={pickImage}>
            <Text style={styles.uploadBtnText}>📷 کیمرہ</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.uploadBtn} onPress={pickFromGallery}>
            <Text style={styles.uploadBtnText}>🖼️ گیلری</Text>
          </TouchableOpacity>
        </View>
      </View>

      {!!error && <Text style={styles.errorText}>{error}</Text>}

      <TouchableOpacity
        style={[styles.analyzeBtn, !imageUri && styles.analyzeBtnDisabled]}
        onPress={analyze}
        disabled={!imageUri}
      >
        <Text style={styles.analyzeBtnText}>تجزیہ شروع کریں</Text>
      </TouchableOpacity>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.BACKGROUND },
  content: { padding: 20, paddingBottom: 40 },
  loadingContainer: { flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: Colors.BACKGROUND },
  loadingText: { fontSize: 18, color: Colors.PRIMARY, marginTop: 16, fontWeight: '600' },
  loadingSubText: { fontSize: 13, color: Colors.GRAY, marginTop: 4 },
  header: { backgroundColor: Colors.PRIMARY, borderRadius: 16, padding: 20, marginBottom: 16, alignItems: 'center' },
  headerTitle: { fontSize: 22, fontWeight: 'bold', color: Colors.SECONDARY },
  headerSub: { fontSize: 13, color: '#ffffff99', marginTop: 4 },
  chipsRow: { marginBottom: 16 },
  chip: { backgroundColor: Colors.SURFACE, borderRadius: 20, paddingHorizontal: 14, paddingVertical: 6, marginRight: 8, borderWidth: 1, borderColor: Colors.GOLD_BORDER },
  chipText: { fontSize: 13, color: Colors.PRIMARY, fontWeight: '500' },
  uploadArea: { backgroundColor: Colors.SURFACE, borderRadius: 14, padding: 24, alignItems: 'center', borderWidth: 2, borderColor: Colors.GOLD_BORDER, borderStyle: 'dashed', marginBottom: 20 },
  uploadIcon: { fontSize: 40, marginBottom: 8 },
  uploadText: { fontSize: 15, color: Colors.GRAY, marginBottom: 16 },
  previewImage: { width: '100%', height: 200, borderRadius: 8, marginBottom: 12, resizeMode: 'contain' },
  uploadButtonRow: { flexDirection: 'row', gap: 12 },
  uploadBtn: { backgroundColor: Colors.PRIMARY, paddingHorizontal: 20, paddingVertical: 10, borderRadius: 8 },
  uploadBtnText: { color: '#fff', fontWeight: '600' },
  errorText: { color: Colors.ACCENT_RED, fontSize: 13, marginBottom: 12, textAlign: 'center' },
  analyzeBtn: { backgroundColor: Colors.PRIMARY, padding: 16, borderRadius: 12, alignItems: 'center' },
  analyzeBtnDisabled: { backgroundColor: Colors.GRAY },
  analyzeBtnText: { color: '#fff', fontSize: 17, fontWeight: '700' },
  typeBadgeRow: { flexDirection: 'row', gap: 10, marginBottom: 14, flexWrap: 'wrap' },
  typeBadge: { backgroundColor: Colors.PRIMARY, paddingHorizontal: 14, paddingVertical: 6, borderRadius: 20 },
  typeBadgeText: { color: '#fff', fontWeight: '700', fontSize: 14 },
  dangerBadge: { backgroundColor: Colors.ACCENT_RED, paddingHorizontal: 14, paddingVertical: 6, borderRadius: 20 },
  dangerBadgeText: { color: '#fff', fontWeight: '700', fontSize: 13 },
  summaryCard: { backgroundColor: '#FFF9EC', borderRadius: 12, padding: 16, marginBottom: 16, borderWidth: 1, borderColor: Colors.GOLD_BORDER },
  summaryLabel: { fontSize: 13, fontWeight: '700', color: Colors.PRIMARY, marginBottom: 8 },
  summaryText: { fontSize: 15, color: Colors.TEXT_DARK, lineHeight: 24 },
  sectionHeading: { fontSize: 17, fontWeight: 'bold', color: Colors.TEXT_DARK, marginBottom: 10 },
  flagCard: { backgroundColor: Colors.SURFACE, borderRadius: 12, padding: 14, marginBottom: 10, borderLeftWidth: 5, elevation: 2, shadowColor: '#000', shadowOpacity: 0.05, shadowRadius: 3, shadowOffset: { width: 0, height: 1 } },
  flagHeader: { flexDirection: 'row', alignItems: 'center', gap: 8, marginBottom: 4 },
  flagEmoji: { fontSize: 18 },
  riskPill: { paddingHorizontal: 8, paddingVertical: 2, borderRadius: 10 },
  riskPillText: { color: '#fff', fontSize: 10, fontWeight: '800' },
  flagClause: { flex: 1, fontSize: 13, color: Colors.TEXT_DARK },
  flagDetail: { marginTop: 8, padding: 10, backgroundColor: Colors.GRAY_LIGHT, borderRadius: 8 },
  flagExplanation: { fontSize: 13, color: Colors.TEXT_DARK, lineHeight: 20 },
  expandHint: { fontSize: 11, color: Colors.GRAY, marginTop: 6, textAlign: 'right' },
  safeBox: { backgroundColor: '#DCFCE7', borderRadius: 12, padding: 16, marginBottom: 16, alignItems: 'center' },
  safeText: { fontSize: 15, color: Colors.SUCCESS, fontWeight: '600', textAlign: 'center' },
  resetBtn: { backgroundColor: Colors.SECONDARY, padding: 14, borderRadius: 12, alignItems: 'center', marginTop: 8 },
  resetBtnText: { color: Colors.TEXT_DARK, fontSize: 16, fontWeight: '700' },
});
