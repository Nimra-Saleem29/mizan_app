import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { createNativeStackNavigator } from '@react-navigation/native-stack';

import HomeScreen    from '../screens/HomeScreen';
import ScannerScreen from '../screens/ScannerScreen';
import HistoryScreen from '../screens/HistoryScreen';
import ProfileScreen from '../screens/ProfileScreen';
import ChatScreen    from '../screens/ChatScreen';
import FIRScreen     from '../screens/FIRScreen';
import DocumentScreen from '../screens/DocumentScreen';
import RightsScreen  from '../screens/RightsScreen';

import Colors, { Shadow } from '../constants/colors';
import { RootStackParamList, TabParamList } from './types';

const Tab       = createBottomTabNavigator<TabParamList>();
const RootStack = createNativeStackNavigator<RootStackParamList>();

// Icon-only tab bar — no labels, large touch targets
const TAB_ICONS: Record<string, { active: string; inactive: string }> = {
  Home:    { active: '⚖️',  inactive: '⚖️'  },
  Scanner: { active: '📷',  inactive: '📷'  },
  History: { active: '🕐',  inactive: '🕐'  },
  Profile: { active: '👤',  inactive: '👤'  },
};

function TabNavigator() {
  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        headerShown: false,
        tabBarShowLabel: false,
        tabBarStyle: styles.tabBar,
        tabBarIcon: ({ focused }) => {
          const icons = TAB_ICONS[route.name];
          return (
            <View style={[styles.tabIconWrap, focused && styles.tabIconWrapActive]}>
              <Text style={[styles.tabIcon, { fontSize: focused ? 22 : 20 }]}>
                {icons.active}
              </Text>
              {focused && <View style={styles.activeDot} />}
            </View>
          );
        },
      })}
    >
      <Tab.Screen name="Home"    component={HomeScreen}    />
      <Tab.Screen name="Scanner" component={ScannerScreen} />
      <Tab.Screen name="History" component={HistoryScreen} />
      <Tab.Screen name="Profile" component={ProfileScreen} />
    </Tab.Navigator>
  );
}

// Placeholder screens
function QueryResultScreen()   { return <View style={s.ph}><Text style={s.pt}>⚖️ نتیجہ</Text></View>; }
function FIRResultScreen()     { return <View style={s.ph}><Text style={s.pt}>🚨 FIR نتیجہ</Text></View>; }
function DocumentResultScreen(){ return <View style={s.ph}><Text style={s.pt}>📄 دستاویز نتیجہ</Text></View>; }

export default function AppNavigator() {
  return (
    <RootStack.Navigator>
      <RootStack.Screen name="Tabs"           component={TabNavigator}          options={{ headerShown: false }} />
      <RootStack.Screen name="Chat"           component={ChatScreen}            options={modalOpts('وکیل چیٹ')} />
      <RootStack.Screen name="FIRAnalyze"     component={FIRScreen}             options={modalOpts('FIR تجزیہ')} />
      <RootStack.Screen name="DocAnalyze"     component={DocumentScreen}        options={modalOpts('دستاویز')} />
      <RootStack.Screen name="Rights"         component={RightsScreen}          options={modalOpts('میرے حقوق')} />
      <RootStack.Screen name="QueryResult"    component={QueryResultScreen}     options={modalOpts('جواب')} />
      <RootStack.Screen name="FIRResult"      component={FIRResultScreen}       options={modalOpts('FIR نتیجہ')} />
      <RootStack.Screen name="DocumentResult" component={DocumentResultScreen}  options={modalOpts('نتیجہ')} />
    </RootStack.Navigator>
  );
}

const modalOpts = (title: string) => ({
  presentation: 'card' as const,
  headerShown: true,
  title,
  headerStyle: { backgroundColor: Colors.PRIMARY },
  headerTintColor: Colors.TEXT_ON_GREEN,
  headerTitleStyle: { fontWeight: '700' as const, fontSize: 18 },
  headerBackTitle: 'واپس',
});

const styles = StyleSheet.create({
  tabBar: {
    height: 72,
    backgroundColor: Colors.SURFACE,
    borderTopWidth: 1,
    borderTopColor: Colors.BORDER,
    paddingBottom: 10,
    paddingTop: 8,
    ...Shadow.MD,
  },
  tabIconWrap: {
    alignItems: 'center',
    justifyContent: 'center',
    width: 52,
    height: 44,
    borderRadius: 14,
  },
  tabIconWrapActive: {
    backgroundColor: Colors.PRIMARY_SUBTLE,
  },
  tabIcon: {
    lineHeight: 28,
  },
  activeDot: {
    width: 4,
    height: 4,
    borderRadius: 2,
    backgroundColor: Colors.PRIMARY,
    marginTop: 2,
  },
});

const s = StyleSheet.create({
  ph: { flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: Colors.BACKGROUND },
  pt: { fontSize: 20, color: Colors.PRIMARY, fontWeight: 'bold' },
});
