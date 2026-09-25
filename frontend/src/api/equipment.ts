import api from './client';
import type { Equipment, EquipmentCreate, EquipmentUpdate } from '@/schemas/equipment';

export async function listEquipment(): Promise<Equipment[]> {
  const res = await api.get<Equipment[]>('/equipment/');
  return res.data;
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
