import api from './client';
import type { DiagnosisRequest, DiagnosisResponse } from '@/schemas/diagnosis';

export async function diagnose(data: DiagnosisRequest): Promise<DiagnosisResponse> {
  const res = await api.post<DiagnosisResponse>('/ai/diagnose', data, { timeout: 180000 });
  return res.data;
}
