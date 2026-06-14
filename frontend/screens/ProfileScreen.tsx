import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import Colors, { Spacing, Radius, Shadow } from '../constants/colors';

const MENU = [
  { emoji: '🌐', label: 'زبان تبدیل کریں', sub: 'Change Language' },
  { emoji: '🔔', label: 'اطلاعات', sub: 'Notifications' },
  { emoji: '📞', label: 'ہم سے رابطہ', sub: 'Contact Us' },
  { emoji: '🔒', label: 'پرائیویسی', sub: 'Privacy Policy' },
  { emoji: 'ℹ️', label: 'وکیل کے بارے میں', sub: 'About Wakeel' },
];

export default function ProfileScreen() {
  return (
    <View style={styles.root}>
      <View style={styles.header}>
        <View style={styles.avatar}><Text style={styles.avatarText}>👤</Text></View>
        <Text style={styles.name}>مہمان صارف</Text>
        <Text style={styles.nameEn}>Guest User</Text>
        <TouchableOpacity style={styles.loginBtn}>
          <Text style={styles.loginBtnText}>لاگ ان کریں (Login)</Text>
        </TouchableOpacity>
      </View>
      <View style={styles.menu}>
        {MENU.map((item, i) => (
          <TouchableOpacity key={i} style={styles.menuItem} activeOpacity={0.75}>
            <Text style={styles.menuEmoji}>{item.emoji}</Text>
            <View style={styles.menuText}>
              <Text style={styles.menuLabel}>{item.label}</Text>
              <Text style={styles.menuSub}>{item.sub}</Text>
            </View>
            <Text style={styles.menuArrow}>›</Text>
          </TouchableOpacity>
        ))}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: Colors.BACKGROUND },
  header: { backgroundColor: Colors.PRIMARY, paddingTop: 54, paddingBottom: 28, alignItems: 'center', borderBottomLeftRadius: 28, borderBottomRightRadius: 28, ...Shadow.LG },
  avatar: { width: 72, height: 72, borderRadius: 36, backgroundColor: 'rgba(255,255,255,0.2)', justifyContent: 'center', alignItems: 'center', marginBottom: 10 },
  avatarText: { fontSize: 36 },
  name: { fontSize: 20, fontWeight: '800', color: Colors.TEXT_ON_GREEN },
  nameEn: { fontSize: 13, color: 'rgba(255,255,255,0.6)', marginTop: 2, marginBottom: 14 },
  loginBtn: { backgroundColor: 'rgba(255,255,255,0.15)', paddingHorizontal: 24, paddingVertical: 9, borderRadius: Radius.FULL, borderWidth: 1.5, borderColor: 'rgba(255,255,255,0.4)' },
  loginBtnText: { color: Colors.TEXT_ON_GREEN, fontWeight: '700', fontSize: 14 },
  menu: { padding: Spacing.MD, gap: Spacing.SM },
  menuItem: { backgroundColor: Colors.SURFACE, borderRadius: Radius.MD, padding: Spacing.MD, flexDirection: 'row', alignItems: 'center', gap: Spacing.MD, ...Shadow.SM },
  menuEmoji: { fontSize: 22, width: 32, textAlign: 'center' },
  menuText: { flex: 1 },
  menuLabel: { fontSize: 15, fontWeight: '700', color: Colors.TEXT_PRIMARY },
  menuSub: { fontSize: 11, color: Colors.TEXT_MUTED, marginTop: 1 },
  menuArrow: { fontSize: 22, color: Colors.TEXT_MUTED },
});
