import { NavigatorScreenParams } from '@react-navigation/native';
import type { QueryResponse, FIRAnalysisResponse, DocumentAnalysisResponse } from '../utils/api';

export type TabParamList = {
  Home:    undefined;
  Scanner: undefined;
  History: undefined;
  Profile: undefined;
};

export type RootStackParamList = {
  Tabs:           NavigatorScreenParams<TabParamList>;
  Chat:           undefined;
  QueryResult:    { result: QueryResponse; question: string };
  FIRAnalyze:     undefined;
  FIRResult:      { result: FIRAnalysisResponse };
  DocAnalyze:     undefined;
  DocumentResult: { result: DocumentAnalysisResponse };
  Rights:         { scenarioKey: string };
};

export type AuthStackParamList = {
  Welcome: undefined;
  Login:   undefined;
  Signup:  undefined;
};
