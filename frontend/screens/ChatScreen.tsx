import React, { useState, useRef } from 'react';
import {
  View, Text, TextInput, TouchableOpacity, FlatList,
  StyleSheet, KeyboardAvoidingView, Platform, ActivityIndicator, Alert,
} from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { RootStackParamList } from '../navigation/types';
import { askLegalQuery, QueryResponse, Citation } from '../utils/api';
import Colors from '../constants/colors';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  text: string;
  citations?: Citation[];
  domain?: string;
}

export default function ChatScreen() {
  const navigation = useNavigation<NativeStackNavigationProp<RootStackParamList>>();
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '0',
      role: 'assistant',
      text: 'السلام علیکم! میں وکیل ہوں۔ آپ کا قانونی سوال پوچھیں۔\n\n(Assalam u Alaikum! I am Wakeel. Ask your legal question in Urdu, Roman Urdu, or English.)',
    },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const flatListRef = useRef<FlatList>(null);

  const detectLanguage = (text: string): string => {
  // Urdu script characters
  if (/[\u0600-\u06FF]/.test(text)) return 'urdu';
  // Roman Urdu signal words
  const romanUrduWords = [
    'hai', 'hain', 'mujhe', 'mera', 'meri', 'karo', 'kya',
    'nahi', 'nahin', 'aur', 'lekin', 'karlia', 'karlia',
    'giraftaar', 'wakeel', 'adalat', 'qanun', 'fir', 'bail',
    'talaq', 'kiraya', 'naukri', 'tankhwah', 'makan', 'malik',
    'police', 'thana', 'muqadma', 'darkhwast', 'jan', 'bhai',
  ];
  const lower = text.toLowerCase();
  const hasRomanUrdu = romanUrduWords.some(word => lower.includes(word));
  if (hasRomanUrdu) return 'roman_urdu';
  return 'english';
};

  const sendMessage = async () => {
    if (!input.trim() || loading) return;

    const userMsg: Message = {
      id: Date.now().toString(),
      role: 'user',
      text: input.trim(),
    };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    try {
      const response: QueryResponse = await askLegalQuery({
        query_text: userMsg.text,
        language: detectLanguage(userMsg.text),
        input_type: 'text',
      });

      const assistantMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        text: response.answer,
        citations: response.citations,
        domain: response.legal_domain,
      };
      setMessages(prev => [...prev, assistantMsg]);
    } catch (error) {
      setMessages(prev => [...prev, {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        text: 'معذرت، ابھی جواب نہیں مل سکا۔ انٹرنیٹ کنکشن چیک کریں۔\n(Sorry, could not get a response. Check your connection.)',
      }]);
    } finally {
      setLoading(false);
      setTimeout(() => flatListRef.current?.scrollToEnd({ animated: true }), 100);
    }
  };

  const renderMessage = ({ item }: { item: Message }) => {
    const isUser = item.role === 'user';
    return (
      <View style={[styles.msgRow, isUser ? styles.msgRowUser : styles.msgRowBot]}>
        {!isUser && <Text style={styles.botAvatar}>⚖️</Text>}
        <View style={[styles.bubble, isUser ? styles.bubbleUser : styles.bubbleBot]}>
          <Text style={[styles.bubbleText, isUser ? styles.textUser : styles.textBot]}>
            {item.text}
          </Text>
          {/* Citations */}
          {item.citations && item.citations.length > 0 && (
            <View style={styles.citationsBox}>
              <Text style={styles.citationsLabel}>📚 حوالہ جات:</Text>
              {item.citations.map((c, i) => (
                <Text key={i} style={styles.citationItem}>
                  • {c.case_name} — {c.court} ({c.year}){c.section ? ` § ${c.section}` : ''}
                </Text>
              ))}
            </View>
          )}
          {/* Domain badge */}
          {item.domain && (
            <View style={styles.domainBadge}>
              <Text style={styles.domainText}>{item.domain}</Text>
            </View>
          )}
        </View>
      </View>
    );
  };

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      keyboardVerticalOffset={90}
    >
      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.headerEmoji}>⚖️</Text>
        <View>
          <Text style={styles.headerTitle}>وکیل</Text>
          <Text style={styles.headerSub}>AI Legal Assistant</Text>
        </View>
      </View>

      {/* Messages */}
      <FlatList
        ref={flatListRef}
        data={messages}
        keyExtractor={item => item.id}
        renderItem={renderMessage}
        contentContainerStyle={styles.messagesList}
        onContentSizeChange={() => flatListRef.current?.scrollToEnd({ animated: true })}
      />

      {/* Typing indicator */}
      {loading && (
        <View style={styles.typingRow}>
          <ActivityIndicator size="small" color={Colors.PRIMARY} />
          <Text style={styles.typingText}>وکیل سوچ رہا ہے...</Text>
        </View>
      )}

      {/* Input */}
      <View style={styles.inputRow}>
        <TextInput
          style={styles.input}
          value={input}
          onChangeText={setInput}
          placeholder="اپنا قانونی سوال لکھیں..."
          placeholderTextColor={Colors.GRAY}
          multiline
          maxLength={500}
          onSubmitEditing={sendMessage}
        />
        <TouchableOpacity
          style={[styles.sendBtn, (!input.trim() || loading) && styles.sendBtnDisabled]}
          onPress={sendMessage}
          disabled={!input.trim() || loading}
        >
          <Text style={styles.sendIcon}>➤</Text>
        </TouchableOpacity>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.BACKGROUND },
  header: {
    backgroundColor: Colors.PRIMARY,
    flexDirection: 'row',
    alignItems: 'center',
    paddingTop: 50,
    paddingBottom: 16,
    paddingHorizontal: 20,
    gap: 12,
  },
  headerEmoji: { fontSize: 32 },
  headerTitle: { fontSize: 22, fontWeight: 'bold', color: Colors.SECONDARY },
  headerSub: { fontSize: 12, color: '#ffffff99' },
  messagesList: { padding: 16, paddingBottom: 8 },
  msgRow: { flexDirection: 'row', marginBottom: 14, alignItems: 'flex-end' },
  msgRowUser: { justifyContent: 'flex-end' },
  msgRowBot: { justifyContent: 'flex-start' },
  botAvatar: { fontSize: 22, marginRight: 8, marginBottom: 4 },
  bubble: {
    maxWidth: '82%',
    borderRadius: 18,
    padding: 12,
    paddingHorizontal: 14,
  },
  bubbleUser: {
    backgroundColor: Colors.PRIMARY,
    borderBottomRightRadius: 4,
  },
  bubbleBot: {
    backgroundColor: Colors.SURFACE,
    borderBottomLeftRadius: 4,
    elevation: 2,
    shadowColor: '#000',
    shadowOpacity: 0.06,
    shadowRadius: 4,
    shadowOffset: { width: 0, height: 2 },
  },
  bubbleText: { fontSize: 15, lineHeight: 22 },
  textUser: { color: '#fff' },
  textBot: { color: Colors.TEXT_DARK },
  citationsBox: {
    marginTop: 10,
    padding: 8,
    backgroundColor: Colors.GRAY_LIGHT,
    borderRadius: 8,
    borderLeftWidth: 3,
    borderLeftColor: Colors.SECONDARY,
  },
  citationsLabel: { fontSize: 12, fontWeight: '700', color: Colors.PRIMARY, marginBottom: 4 },
  citationItem: { fontSize: 11, color: Colors.TEXT_DARK, lineHeight: 18 },
  domainBadge: {
    marginTop: 8,
    alignSelf: 'flex-start',
    backgroundColor: Colors.GOLD_BORDER,
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 10,
  },
  domainText: { fontSize: 10, color: Colors.PRIMARY, fontWeight: '600', textTransform: 'uppercase' },
  typingRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingVertical: 8,
    gap: 8,
  },
  typingText: { fontSize: 13, color: Colors.GRAY, fontStyle: 'italic' },
  inputRow: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    padding: 12,
    paddingBottom: 20,
    backgroundColor: Colors.SURFACE,
    borderTopWidth: 1,
    borderTopColor: Colors.GOLD_BORDER,
    gap: 10,
  },
  input: {
    flex: 1,
    backgroundColor: Colors.GRAY_LIGHT,
    borderRadius: 22,
    paddingHorizontal: 16,
    paddingVertical: 10,
    fontSize: 15,
    color: Colors.TEXT_DARK,
    maxHeight: 120,
    minHeight: 44,
  },
  sendBtn: {
    backgroundColor: Colors.PRIMARY,
    width: 44,
    height: 44,
    borderRadius: 22,
    justifyContent: 'center',
    alignItems: 'center',
  },
  sendBtnDisabled: { backgroundColor: Colors.GRAY },
  sendIcon: { color: '#fff', fontSize: 18 },
});
