import React, { useEffect, useState, useRef } from 'react';
import { View, Text, StyleSheet, Animated, StatusBar } from 'react-native';
import { NavigationContainer } from '@react-navigation/native';
import AppNavigator from './navigation/AppNavigator';
import AuthNavigator from './navigation/AuthNavigator';
import Colors from './constants/colors';

// ─── Supabase (stub-safe) ─────────────────────────────────────────────────────
// Replace with real client once Supabase is configured:
// import { createClient } from '@supabase/supabase-js';
// const supabase = createClient(process.env.EXPO_PUBLIC_SUPABASE_URL!, process.env.EXPO_PUBLIC_SUPABASE_ANON_KEY!);
//
// For now using a stub so the app runs without Supabase keys:
const supabase = {
  auth: {
    getSession: async () => ({ data: { session: null } }),
    onAuthStateChange: (_cb: any) => ({
      data: { subscription: { unsubscribe: () => {} } },
    }),
  },
};

// ─── Animated Splash ──────────────────────────────────────────────────────────
function SplashScreen() {
  const fadeAnim = useRef(new Animated.Value(0)).current;
  const scaleAnim = useRef(new Animated.Value(0.7)).current;

  useEffect(() => {
    Animated.parallel([
      Animated.timing(fadeAnim, { toValue: 1, duration: 900, useNativeDriver: true }),
      Animated.spring(scaleAnim, { toValue: 1, friction: 5, tension: 60, useNativeDriver: true }),
    ]).start();
  }, []);

  return (
    <View style={styles.splash}>
      <Animated.View style={{ opacity: fadeAnim, transform: [{ scale: scaleAnim }], alignItems: 'center' }}>
        <Text style={styles.splashIcon}>⚖️</Text>
        <Text style={styles.splashName}>وکیل</Text>
        <Text style={styles.splashLatin}>WAKEEL</Text>
        <Text style={styles.splashTagline}>ہر زبان میں انصاف</Text>
      </Animated.View>
    </View>
  );
}

// ─── Root App ─────────────────────────────────────────────────────────────────
export default function App() {
  // null = checking | true = authenticated | false = not authenticated
  const [authState, setAuthState] = useState<boolean | null>(true);

  // useEffect disabled until Supabase is configured
// useEffect(() => { ... }, []);

  return (
    <>
      <StatusBar barStyle="light-content" backgroundColor={Colors.PRIMARY} />
      <NavigationContainer>
        {authState === null && <SplashScreen />}
        {authState === true && <AppNavigator />}
        {authState === false && <AuthNavigator />}
      </NavigationContainer>
    </>
  );
}

const styles = StyleSheet.create({
  splash: { flex: 1, backgroundColor: Colors.PRIMARY, justifyContent: 'center', alignItems: 'center' },
  splashIcon: { fontSize: 80, marginBottom: 20 },
  splashName: { fontSize: 56, fontWeight: 'bold', color: Colors.SECONDARY, letterSpacing: 2 },
  splashLatin: { fontSize: 15, color: Colors.SURFACE, letterSpacing: 10, fontWeight: '300', marginTop: 4, opacity: 0.65 },
  splashTagline: { fontSize: 16, color: Colors.SURFACE, marginTop: 24, opacity: 0.8 },
});
