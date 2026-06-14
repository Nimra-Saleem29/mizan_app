import React, { useState } from 'react';
import {
  View, Text, TextInput, TouchableOpacity, ScrollView,
  StyleSheet, ActivityIndicator, Alert, Image,
} from 'react-native';
import * as ImagePicker from 'expo-image-picker';
import { analyzeFIRImage, analyzeFIRText, FIRAnalysisResponse } from '../utils/api';
import Colors from '../constants/colors';

type Step = 'input' | 'loading' | 'result';

export default function FIRScreen() {
  const [step, setStep] = useState<Step>('input');
  const [inputMode, setInputMode] = useState<'image' | 'text'>('image');
  const [imageUri, setImageUri] = useState<string | null>(null);
  const [firText, setFirText] = useState('');
  const [result, setResult] = useState<FIRAnalysisResponse | null>(null);
  const [error, setError] = useState('');

  const pickImage = async () => {
    const permission = await ImagePicker.requestCameraPermissionsAsync();
    if (!permission.granted) {
      Alert.alert('اجازت درکار ہے', 'کیمرہ استعمال کرنے کی اجازت دیں۔');
      return;
    }
    const result = await ImagePicker.launchCameraAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      quality: 0.9,
    });
    if (!result.canceled) setImageUri(result.assets[0].uri);
  };

  const pickFromGallery = async () => {
    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      quality: 0.9,
    });
    if (!result.canceled) setImageUri(result.assets[0].uri);
  };

  const analyze = async () => {
    setError('');
    setStep('loading');
    try {
      let data: FIRAnalysisResponse;
      if (inputMode === 'image' && imageUri) {
        data = await analyzeFIRImage(imageUri);
      } else {
        data = await analyzeFIRText(firText);
      }
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
    setFirText('');
    setError('');
  };

  // ── Loading ──────────────────────────────────────────────────────────────
  if (step === 'loading') {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color={Colors.PRIMARY} />
        <Text style={styles.loadingText}>FIR کا تجزیہ ہو رہا ہے...</Text>
        <Text style={styles.loadingSubText}>(Analyzing FIR...)</Text>
      </View>
    );
  }

  // ── Result ───────────────────────────────────────────────────────────────
  if (step === 'result' && result) {
    return (
      <ScrollView style={styles.container} contentContainerStyle={styles.content}>
        {/* Summary box */}
        <View style={[styles.summaryBox, { backgroundColor: result.is_bailable ? Colors.SUCCESS : Colors.ACCENT_RED }]}>
          <Text style={styles.summaryTitle}>
            اس FIR میں {result.sections.length} دفعات ہیں
          </Text>
          <View style={styles.bailBadge}>
            <Text style={styles.bailText}>
              {result.is_bailable ? '✅ ضمانت ہو سکتی ہے' : '🚫 ضمانت نہیں ہو سکتی'}
            </Text>
          </View>
        </View>

        {/* Plain explanation */}
        <View style={styles.card}>
          <Text style={styles.cardLabel}>📋 خلاصہ</Text>
          <Text style={styles.explanationText}>{result.plain_explanation}</Text>
        </View>

        {/* Sections breakdown */}
        <Text style={styles.sectionHeading}>دفعات کی تفصیل</Text>
        {result.sections.map((sec, i) => (
          <View key={i} style={styles.sectionCard}>
            <Text style={styles.sectionNumber}>دفعہ {sec.section_number}</Text>
            <Text style={styles.sectionTitle}>{sec.title}</Text>
            <Text style={styles.sectionExplanation}>{sec.explanation}</Text>
            <View style={styles.punishmentRow}>
              <Text style={styles.punishmentText}>سزا: {sec.min_punishment} — {sec.max_punishment}</Text>
              <View style={[styles.bailChip, { backgroundColor: sec.bailable ? Colors.SUCCESS : Colors.ACCENT_RED }]}>
                <Text style={styles.bailChipText}>{sec.bailable ? 'ضمانتی' : 'غیر ضمانتی'}</Text>
              </View>
            </View>
          </View>
        ))}

        {/* Flags */}
        {result.flags.length > 0 && (
          <View style={styles.flagsBox}>
            <Text style={styles.flagsTitle}>⚠️ ممکنہ خامیاں</Text>
            {result.flags.map((f, i) => (
              <Text key={i} style={styles.flagItem}>• {f}</Text>
            ))}
          </View>
        )}

        {/* Advice */}
        <View style={styles.adviceBox}>
          <Text style={styles.adviceText}>
            فوری طور پر کسی وکیل سے رابطہ کریں۔ ضمانت کی صورت میں مجسٹریٹ کے سامنے ضمانت کی درخواست دیں۔
          </Text>
        </View>

        {/* Reset button */}
        <TouchableOpacity style={styles.resetBtn} onPress={reset}>
          <Text style={styles.resetBtnText}>نیا FIR تجزیہ</Text>
        </TouchableOpacity>
      </ScrollView>
    );
  }

  // ── Input ─────────────────────────────────────────────────────────────────
  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>🚨 FIR تجزیہ</Text>
        <Text style={styles.headerSub}>اپنی FIR اپلوڈ کریں یا متن لکھیں</Text>
      </View>

      {/* Mode toggle */}
      <View style={styles.toggleRow}>
        <TouchableOpacity
          style={[styles.toggleBtn, inputMode === 'image' && styles.toggleActive]}
          onPress={() => setInputMode('image')}
        >
          <Text style={[styles.toggleText, inputMode === 'image' && styles.toggleTextActive]}>
            📷 تصویر
          </Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.toggleBtn, inputMode === 'text' && styles.toggleActive]}
          onPress={() => setInputMode('text')}
        >
          <Text style={[styles.toggleText, inputMode === 'text' && styles.toggleTextActive]}>
            ✏️ متن
          </Text>
        </TouchableOpacity>
      </View>

      {/* Image mode */}
      {inputMode === 'image' && (
        <View style={styles.uploadArea}>
          {imageUri ? (
            <Image source={{ uri: imageUri }} style={styles.previewImage} />
          ) : (
            <Text style={styles.uploadPlaceholder}>📄 FIR کی تصویر یہاں آئے گی</Text>
          )}
          <View style={styles.imageButtonRow}>
            <TouchableOpacity style={styles.imageBtn} onPress={pickImage}>
              <Text style={styles.imageBtnText}>📷 کیمرہ</Text>
            </TouchableOpacity>
            <TouchableOpacity style={styles.imageBtn} onPress={pickFromGallery}>
              <Text style={styles.imageBtnText}>🖼️ گیلری</Text>
            </TouchableOpacity>
          </View>
        </View>
      )}

      {/* Text mode */}
      {inputMode === 'text' && (
        <TextInput
          style={styles.textInput}
          value={firText}
          onChangeText={setFirText}
          placeholder="FIR کا متن یہاں paste کریں..."
          placeholderTextColor={Colors.GRAY}
          multiline
          numberOfLines={8}
        />
      )}

      {/* Error */}
      {!!error && <Text style={styles.errorText}>{error}</Text>}

      {/* Analyze button */}
      <TouchableOpacity
        style={[
          styles.analyzeBtn,
          (inputMode === 'image' ? !imageUri : !firText.trim()) && styles.analyzeBtnDisabled,
        ]}
        onPress={analyze}
        disabled={inputMode === 'image' ? !imageUri : !firText.trim()}
      >
        <Text style={styles.analyzeBtnText}>تجزیہ کریں (Analyze)</Text>
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
  header: { backgroundColor: Colors.PRIMARY, borderRadius: 16, padding: 20, marginBottom: 20, alignItems: 'center' },
  headerTitle: { fontSize: 24, fontWeight: 'bold', color: Colors.SECONDARY },
  headerSub: { fontSize: 13, color: '#ffffff99', marginTop: 4 },
  toggleRow: { flexDirection: 'row', gap: 12, marginBottom: 20 },
  toggleBtn: { flex: 1, padding: 12, borderRadius: 10, borderWidth: 2, borderColor: Colors.GRAY, alignItems: 'center' },
  toggleActive: { borderColor: Colors.PRIMARY, backgroundColor: Colors.PRIMARY + '15' },
  toggleText: { fontSize: 15, color: Colors.GRAY, fontWeight: '600' },
  toggleTextActive: { color: Colors.PRIMARY },
  uploadArea: { backgroundColor: Colors.SURFACE, borderRadius: 12, padding: 20, alignItems: 'center', borderWidth: 2, borderColor: Colors.GOLD_BORDER, borderStyle: 'dashed', marginBottom: 20 },
  uploadPlaceholder: { fontSize: 16, color: Colors.GRAY, marginBottom: 16 },
  previewImage: { width: '100%', height: 200, borderRadius: 8, marginBottom: 12, resizeMode: 'contain' },
  imageButtonRow: { flexDirection: 'row', gap: 12 },
  imageBtn: { backgroundColor: Colors.PRIMARY, paddingHorizontal: 20, paddingVertical: 10, borderRadius: 8 },
  imageBtnText: { color: '#fff', fontWeight: '600' },
  textInput: { backgroundColor: Colors.SURFACE, borderRadius: 12, padding: 14, fontSize: 14, color: Colors.TEXT_DARK, borderWidth: 1, borderColor: Colors.GOLD_BORDER, minHeight: 160, textAlignVertical: 'top', marginBottom: 20 },
  errorText: { color: Colors.ACCENT_RED, fontSize: 13, marginBottom: 12, textAlign: 'center' },
  analyzeBtn: { backgroundColor: Colors.PRIMARY, padding: 16, borderRadius: 12, alignItems: 'center' },
  analyzeBtnDisabled: { backgroundColor: Colors.GRAY },
  analyzeBtnText: { color: '#fff', fontSize: 17, fontWeight: '700' },
  summaryBox: { borderRadius: 16, padding: 20, alignItems: 'center', marginBottom: 16 },
  summaryTitle: { fontSize: 18, fontWeight: 'bold', color: '#fff', marginBottom: 10 },
  bailBadge: { backgroundColor: 'rgba(255,255,255,0.25)', paddingHorizontal: 16, paddingVertical: 6, borderRadius: 20 },
  bailText: { color: '#fff', fontWeight: '700', fontSize: 15 },
  card: { backgroundColor: Colors.SURFACE, borderRadius: 12, padding: 16, marginBottom: 16, elevation: 2, shadowColor: '#000', shadowOpacity: 0.06, shadowRadius: 4, shadowOffset: { width: 0, height: 2 } },
  cardLabel: { fontSize: 13, fontWeight: '700', color: Colors.PRIMARY, marginBottom: 8 },
  explanationText: { fontSize: 15, color: Colors.TEXT_DARK, lineHeight: 24 },
  sectionHeading: { fontSize: 17, fontWeight: 'bold', color: Colors.TEXT_DARK, marginBottom: 10 },
  sectionCard: { backgroundColor: Colors.SURFACE, borderRadius: 12, padding: 16, marginBottom: 12, borderLeftWidth: 4, borderLeftColor: Colors.SECONDARY, elevation: 2, shadowColor: '#000', shadowOpacity: 0.05, shadowRadius: 3, shadowOffset: { width: 0, height: 1 } },
  sectionNumber: { fontSize: 20, fontWeight: 'bold', color: Colors.SECONDARY, marginBottom: 4 },
  sectionTitle: { fontSize: 16, fontWeight: '600', color: Colors.TEXT_DARK, marginBottom: 6 },
  sectionExplanation: { fontSize: 14, color: Colors.TEXT_DARK, lineHeight: 21, marginBottom: 10 },
  punishmentRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  punishmentText: { fontSize: 12, color: Colors.GRAY, flex: 1 },
  bailChip: { paddingHorizontal: 10, paddingVertical: 4, borderRadius: 12 },
  bailChipText: { color: '#fff', fontSize: 11, fontWeight: '700' },
  flagsBox: { backgroundColor: '#FFF3CD', borderRadius: 12, padding: 16, marginBottom: 16, borderLeftWidth: 4, borderLeftColor: Colors.WARNING },
  flagsTitle: { fontSize: 15, fontWeight: '700', color: Colors.WARNING, marginBottom: 8 },
  flagItem: { fontSize: 13, color: Colors.TEXT_DARK, lineHeight: 22 },
  adviceBox: { backgroundColor: Colors.SURFACE, borderRadius: 12, padding: 16, marginBottom: 20, borderWidth: 2, borderColor: Colors.PRIMARY },
  adviceText: { fontSize: 14, color: Colors.TEXT_DARK, lineHeight: 22, textAlign: 'center' },
  resetBtn: { backgroundColor: Colors.SECONDARY, padding: 14, borderRadius: 12, alignItems: 'center' },
  resetBtnText: { color: Colors.TEXT_DARK, fontSize: 16, fontWeight: '700' },
});
