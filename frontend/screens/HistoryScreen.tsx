import React from 'react';
import { View, Text, StyleSheet, ScrollView, TouchableOpacity } from 'react-native';
import Colors, { Spacing, Radius, Shadow } from '../constants/colors';

const MOCK_HISTORY = [
  { id: '1', q: 'FIR میں دفعہ 302 کیا ہے؟', time: 'آج', domain: 'فوجداری' },
  { id: '2', q: 'مالک مجھے گھر سے نہیں نکال سکتا؟', time: 'کل', domain: 'جائیداد' },
  { id: '3', q: 'Salary na milne par kya karun?', time: '2 دن پہلے', domain: 'ملازمت' },
];

export default function HistoryScreen() {
  return (
    <View style={styles.root}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>🕐 تاریخ</Text>
        <Text style={styles.headerSub}>Chat History</Text>
      </View>
      <ScrollView contentContainerStyle={styles.content}>
        {MOCK_HISTORY.length === 0 ? (
          <View style={styles.empty}>
            <Text style={styles.emptyEmoji}>📭</Text>
            <Text style={styles.emptyText}>ابھی تک کوئی سوال نہیں</Text>
            <Text style={styles.emptyTextEn}>No questions asked yet</Text>
          </View>
        ) : (
          MOCK_HISTORY.map(item => (
            <TouchableOpacity key={item.id} style={styles.historyCard} activeOpacity={0.8}>
              <View style={styles.historyLeft}>
                <Text style={styles.historyQ} numberOfLines={2}>{item.q}</Text>
                <View style={styles.historyMeta}>
                  <View style={styles.domainBadge}>
                    <Text style={styles.domainText}>{item.domain}</Text>
                  </View>
                  <Text style={styles.historyTime}>{item.time}</Text>
                </View>
              </View>
              <Text style={styles.historyArrow}>›</Text>
            </TouchableOpacity>
          ))
        )}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: Colors.BACKGROUND },
  header: { backgroundColor: Colors.PRIMARY, paddingTop: 54, paddingBottom: 20, paddingHorizontal: Spacing.MD, borderBottomLeftRadius: 24, borderBottomRightRadius: 24, ...Shadow.LG },
  headerTitle: { fontSize: 24, fontWeight: '800', color: Colors.TEXT_ON_GREEN },
  headerSub: { fontSize: 13, color: 'rgba(255,255,255,0.6)', marginTop: 2 },
  content: { padding: Spacing.MD, paddingBottom: 40 },
  empty: { alignItems: 'center', marginTop: 80 },
  emptyEmoji: { fontSize: 60, marginBottom: 16 },
  emptyText: { fontSize: 18, fontWeight: '700', color: Colors.TEXT_PRIMARY },
  emptyTextEn: { fontSize: 13, color: Colors.TEXT_MUTED, marginTop: 4 },
  historyCard: { backgroundColor: Colors.SURFACE, borderRadius: Radius.MD, padding: Spacing.MD, marginBottom: Spacing.SM, flexDirection: 'row', alignItems: 'center', ...Shadow.SM },
  historyLeft: { flex: 1 },
  historyQ: { fontSize: 15, fontWeight: '600', color: Colors.TEXT_PRIMARY, marginBottom: 8, lineHeight: 22 },
  historyMeta: { flexDirection: 'row', alignItems: 'center', gap: Spacing.SM },
  domainBadge: { backgroundColor: Colors.PRIMARY_SUBTLE, paddingHorizontal: 10, paddingVertical: 3, borderRadius: Radius.FULL },
  domainText: { fontSize: 11, color: Colors.PRIMARY, fontWeight: '700' },
  historyTime: { fontSize: 11, color: Colors.TEXT_MUTED },
  historyArrow: { fontSize: 24, color: Colors.TEXT_MUTED },
});
