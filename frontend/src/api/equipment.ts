import api from './client';
import type { Equipment, EquipmentCreate, EquipmentUpdate } from '@/schemas/equipment';

export async function listEquipment(): Promise<Equipment[]> {
  const res = await api.get<Equipment[]>('/equipment/');
  const data: unknown = res.data;
  if (!Array.isArray(data)) {
    throw new Error('Unexpected equipment API response');
  }
  return data as Equipment[];
}

export async function getEquipment(id: string): Promise<Equipment> {
  const res = await api.get<Equipment>(`/equipment/${id}`);
  return res.data;
}

export async function createEquipment(data: EquipmentCreate): Promise<Equipment> {
  const res = await api.post<Equipment>('/equipment/', data);
  return res.data;
}

export async function updateEquipment(id: string, data: EquipmentUpdate): Promise<Equipment> {
  const res = await api.patch<Equipment>(`/equipment/${id}`, data);
  return res.data;
}
