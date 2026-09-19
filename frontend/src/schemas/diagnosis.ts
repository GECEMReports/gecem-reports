export interface DiagnosisRequest {
  equipment_id: string;
  symptoms?: string;
  thread_id?: string;
  respuesta_seguimiento?: string;
}

export interface DiagnosisResponse {
  interrupted: boolean;
  thread_id?: string | null;
  pregunta?: string | null;
  necesita_mas_info?: boolean;
  pregunta_seguimiento?: string | null;
  problem_type?: string | null;
  diagnosis?: string | null;
  recommendations?: string[] | null;
  parts_needed?: string[] | null;
  estimated_hours?: number | null;
  severity?: 'low' | 'medium' | 'high' | 'critical' | null;
}
