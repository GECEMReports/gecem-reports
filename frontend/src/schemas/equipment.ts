export interface EquipmentCreate {
  brand: string;
  model: string;
  serial_number: string;
  equipment_type: string;
  hours?: number;
  year?: number;
  client_id?: string;
  notes?: string;
}

export interface EquipmentUpdate {
  brand?: string;
  model?: string;
  serial_number?: string;
  equipment_type?: string;
  hours?: number;
  year?: number;
  notes?: string;
}

export interface Equipment {
  id: string;
  tenant_id: string;
  brand: string;
  model: string;
  serial_number: string;
  equipment_type: string;
  hours: number;
  year: number | null;
  client_id: string | null;
  notes: string | null;
  created_at: string;
}
