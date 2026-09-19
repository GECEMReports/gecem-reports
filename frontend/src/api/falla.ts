import api from './client';
import type {
  Falla,
  FallaCreate,
  FallaAgentResponse,
  Refaccion,
} from '@/schemas/falla';

export async function createFalla(data: FallaCreate): Promise<Falla> {
  const res = await api.post<Falla>('/fallas/', data);
  return res.data;
}

export async function listFallas(equipmentId?: string): Promise<Falla[]> {
  const params = equipmentId ? { equipment_id: equipmentId } : {};
  const res = await api.get<Falla[]>('/fallas/', { params });
  return res.data;
}

export async function getFalla(id: string): Promise<Falla> {
  const res = await api.get<Falla>(`/fallas/${id}`);
  return res.data;
}

export async function uploadFallaFoto(
  fallaId: string,
  file: File,
  descripcion?: string
): Promise<{ id: string; filename: string }> {
  const formData = new FormData();
  formData.append('file', file);
  if (descripcion) formData.append('descripcion', descripcion);
  const res = await api.post(`/fallas/${fallaId}/fotos`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return res.data;
}

export async function estructurarFalla(
  equipmentId: string,
  diagnosticoIa: string,
  descripcionMecanico: string
): Promise<FallaAgentResponse> {
  const res = await api.post<FallaAgentResponse>('/ai/estructurar-falla', {
    equipment_id: equipmentId,
    diagnostico_ia: diagnosticoIa,
    descripcion_mecanico: descripcionMecanico,
  }, { timeout: 180000 });
  return res.data;
}

export async function createRefaccion(
  fallaId: string,
  data: { nombre: string; precio_unitario?: number; cantidad?: number }
): Promise<Refaccion> {
  const res = await api.post<Refaccion>(`/fallas/${fallaId}/refacciones`, data);
  return res.data;
}

export async function listRefacciones(fallaId: string): Promise<Refaccion[]> {
  const res = await api.get<Refaccion[]>(`/fallas/${fallaId}/refacciones`);
  return res.data;
}
