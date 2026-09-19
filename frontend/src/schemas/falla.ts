export interface FallaFoto {
  id: string;
  filename: string;
  filepath: string;
  descripcion: string | null;
}

export interface FallaCreate {
  equipment_id: string;
  diagnosis_id?: string;
  parte: string;
  pieza: string;
  descripcion: string;
  causa_raiz?: string;
  prioridad?: string;
  notas?: string;
}

export interface Falla {
  id: string;
  tenant_id: string;
  equipment_id: string;
  diagnosis_id: string | null;
  parte: string;
  pieza: string;
  descripcion: string;
  causa_raiz: string | null;
  prioridad: string;
  status: string;
  notas: string | null;
  created_at: string;
  fotos: FallaFoto[];
}

export interface FallaEstructurada {
  parte: string;
  pieza: string;
  descripcion: string;
  causa_raiz: string;
  prioridad: string;
  severidad: string;
}

export interface FallaAgentResponse {
  necesita_mas_info: boolean;
  pregunta_seguimiento?: string | null;
  falla_estructurada?: FallaEstructurada | null;
}

export interface Refaccion {
  id: string;
  falla_id: string;
  nombre: string;
  numero_parte: string | null;
  cantidad: number;
  precio_unitario: number | null;
  moneda: string;
  proveedor: string | null;
  precio_confirmado: boolean;
  editado_por_mecanico?: boolean;
  status: string;
  created_at: string;
}

export interface RefaccionSugerida {
  nombre: string;
  numero_parte?: string | null;
  pn_verificado?: boolean;
  cantidad: number;
  precio_estimado?: number | null;
  moneda: string;
  prioridad: string;
  precio_confirmado: boolean;
  editado_por_mecanico: boolean;
}

export interface SugerirRefaccionesResponse {
  refacciones: RefaccionSugerida[];
  notas: string;
}

export interface ConfirmarRefaccionItem {
  nombre: string;
  numero_parte?: string | null;
  cantidad: number;
  precio_unitario?: number | null;
  moneda: string;
  prioridad: string;
  precio_confirmado: boolean;
  editado_por_mecanico: boolean;
}
