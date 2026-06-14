import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet, StatusBar } from 'react-native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { useNavigation } from '@react-navigation/native';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import Colors, { Spacing, Radius, Shadow } from '../constants/colors';
import { AuthStackParamList } from './types';

const AuthStack = createNativeStackNavigator<AuthStackParamList>();

function WelcomeScreen() {
  const nav = useNavigation<NativeStackNavigationProp<AuthStackParamList, 'Welcome'>>();
  return (
    <View style={styles.root}>
      <StatusBar barStyle="light-content" backgroundColor={Colors.PRIMARY} />

      {/* Top decorative area */}
      <View style={styles.heroArea}>
        <View style={styles.logoRing}>
          <Text style={styles.logoEmoji}>⚖️</Text>
        </View>
        <Text style={styles.appName}>وکیل</Text>
        <Text style={styles.appLatin}>W A K E E L</Text>
        <View style={styles.taglineBox}>
          <Text style={styles.taglineUrdu}>ہر زبان میں انصاف</Text>
          <Text style={styles.taglineEn}>Justice in Every Language</Text>
        </View>
      </View>

      {/* Feature pills */}
      <View style={styles.featuresRow}>
        {[
          { emoji: '🆓', label: 'بالکل مفت' },
          { emoji: '🔒', label: 'محفوظ' },
          { emoji: '📱', label: 'آسان' },
        ].map((f, i) => (
          <View key={i} style={styles.featurePill}>
            <Text style={styles.featureEmoji}>{f.emoji}</Text>
            <Text style={styles.featureLabel}>{f.label}</Text>
          </View>
        ))}
      </View>

      {/* Buttons */}
      <View style={styles.buttonArea}>
        <TouchableOpacity style={styles.primaryBtn} onPress={() => nav.navigate('Login')} activeOpacity={0.85}>
          <Text style={styles.primaryBtnText}>لاگ ان کریں (Login)</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.secondaryBtn} onPress={() => nav.navigate('Signup')} activeOpacity={0.85}>
          <Text style={styles.secondaryBtnText}>رجسٹر کریں (Sign Up)</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.skipBtn} activeOpacity={0.7}>
          <Text style={styles.skipText}>بغیر اکاؤنٹ جاری رکھیں ›</Text>
          <Text style={styles.skipTextEn}>Continue without account</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

function LoginScreen() {
  const nav = useNavigation<NativeStackNavigationProp<AuthStackParamList>>();
  return (
    <View style={[styles.root, { justifyContent: 'center' }]}>
      <Text style={[styles.appName, { color: Colors.PRIMARY }]}>لاگ ان</Text>
      <Text style={[styles.taglineEn, { color: Colors.TEXT_MUTED, marginTop: 8 }]}>Supabase Auth — coming soon</Text>
      <TouchableOpacity style={[styles.secondaryBtn, { marginTop: 32, borderColor: Colors.PRIMARY }]} onPress={() => nav.goBack()}>
        <Text style={[styles.secondaryBtnText, { color: Colors.PRIMARY }]}>واپس (Back)</Text>
      </TouchableOpacity>
    </View>
  );
}

function SignupScreen() {
  const nav = useNavigation<NativeStackNavigationProp<AuthStackParamList>>();
  return (
    <View style={[styles.root, { justifyContent: 'center' }]}>
      <Text style={[styles.appName, { color: Colors.PRIMARY }]}>رجسٹریشن</Text>
      <Text style={[styles.taglineEn, { color: Colors.TEXT_MUTED, marginTop: 8 }]}>Supabase Auth — coming soon</Text>
      <TouchableOpacity style={[styles.secondaryBtn, { marginTop: 32, borderColor: Colors.PRIMARY }]} onPress={() => nav.goBack()}>
        <Text style={[styles.secondaryBtnText, { color: Colors.PRIMARY }]}>واپس (Back)</Text>
      </TouchableOpacity>
    </View>
  );
}

export default function AuthNavigator() {
  return (
    <AuthStack.Navigator screenOptions={{ headerShown: false }}>
      <AuthStack.Screen name="Welcome" component={WelcomeScreen} />
      <AuthStack.Screen name="Login"   component={LoginScreen}   />
      <AuthStack.Screen name="Signup"  component={SignupScreen}  />
    </AuthStack.Navigator>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: Colors.PRIMARY, paddingHorizontal: Spacing.LG },
  heroArea: { flex: 1, justifyContent: 'center', alignItems: 'center', paddingTop: 60 },
  logoRing: {
    width: 110, height: 110, borderRadius: 55,
    backgroundColor: 'rgba(255,255,255,0.12)',
    justifyContent: 'center', alignItems: 'center',
    marginBottom: 24,
    borderWidth: 2, borderColor: 'rgba(255,255,255,0.2)',
  },
  logoEmoji: { fontSize: 56 },
  appName: { fontSize: 54, fontWeight: '900', color: Colors.PEACH, letterSpacing: 1 },
  appLatin: { fontSize: 13, color: 'rgba(255,255,255,0.5)', letterSpacing: 10, fontWeight: '300', marginTop: 4 },
  taglineBox: { alignItems: 'center', marginTop: 20 },
  taglineUrdu: { fontSize: 18, color: Colors.TEXT_ON_GREEN, fontWeight: '600', opacity: 0.9 },
  taglineEn: { fontSize: 12, color: 'rgba(255,255,255,0.55)', marginTop: 3 },
  featuresRow: { flexDirection: 'row', justifyContent: 'center', gap: 10, marginBottom: 32 },
  featurePill: {
    flexDirection: 'row', alignItems: 'center', gap: 5,
    backgroundColor: 'rgba(255,255,255,0.12)',
    paddingHorizontal: 14, paddingVertical: 8, borderRadius: Radius.FULL,
    borderWidth: 1, borderColor: 'rgba(255,255,255,0.2)',
  },
  featureEmoji: { fontSize: 15 },
  featureLabel: { fontSize: 12, color: Colors.TEXT_ON_GREEN, fontWeight: '600' },
  buttonArea: { paddingBottom: 52, gap: Spacing.SM },
  primaryBtn: {
    backgroundColor: Colors.PEACH, paddingVertical: 17,
    borderRadius: Radius.LG, alignItems: 'center', ...Shadow.LG,
  },
  primaryBtnText: { color: Colors.TEXT_PRIMARY, fontSize: 17, fontWeight: '800' },
  secondaryBtn: {
    borderWidth: 2, borderColor: 'rgba(255,255,255,0.5)',
    paddingVertical: 16, borderRadius: Radius.LG, alignItems: 'center',
  },
  secondaryBtnText: { color: Colors.TEXT_ON_GREEN, fontSize: 17, fontWeight: '700' },
  skipBtn: { alignItems: 'center', paddingVertical: 10 },
  skipText: { color: 'rgba(255,255,255,0.6)', fontSize: 13 },
  skipTextEn: { color: 'rgba(255,255,255,0.4)', fontSize: 11, marginTop: 2 },
});
