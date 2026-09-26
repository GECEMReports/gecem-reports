import api, { fetchPdf, openPdfInNewTab } from './client';
import type {
  Falla,
  FallaCreate,
  FallaAgentResponse,
  Refaccion,
  SugerirRefaccionesResponse,
  ConfirmarRefaccionItem,
  Cotizacion,
  ProcedimientoReparacion,
  ReporteCliente,
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

export async function sugerirRefacciones(fallaId: string): Promise<SugerirRefaccionesResponse> {
  const res = await api.post<SugerirRefaccionesResponse>('/ai/sugerir-refacciones', {
    falla_id: fallaId,
  }, { timeout: 180000 });
  return res.data;
}

export async function confirmarRefacciones(
  fallaId: string,
  refacciones: ConfirmarRefaccionItem[]
): Promise<{ message: string; count: number }> {
  const res = await api.post('/ai/confirmar-refacciones', {
    falla_id: fallaId,
    refacciones,
  });
  return res.data;
}

export async function createCotizacionManual(data: {
  falla_id: string;
  subtotal_refacciones: number;
  mano_de_obra: number;
  moneda?: string;
  notas?: string;
}): Promise<Cotizacion> {
  const res = await api.post<Cotizacion>('/cotizaciones/', {
    ...data,
    tipo: 'manual',
  });
  return res.data;
}

export async function listCotizaciones(fallaId?: string): Promise<Cotizacion[]> {
  const params = fallaId ? { falla_id: fallaId } : {};
  const res = await api.get<Cotizacion[]>('/cotizaciones/', { params });
  return res.data;
}

export async function getCotizacion(id: string): Promise<Cotizacion> {
  const res = await api.get<Cotizacion>(`/cotizaciones/${id}`);
  return res.data;
}

export async function downloadCotizacionPdf(id: string): Promise<void> {
  const blob = await fetchPdf(`/cotizaciones/${id}/pdf`);
  openPdfInNewTab(blob, `cotizacion-${id}.pdf`);
}

// --- Reparaciones ---
export async function listReparaciones(equipmentId?: string): Promise<ProcedimientoReparacion[]> {
  const params = equipmentId ? { equipment_id: equipmentId } : {};
  const res = await api.get<ProcedimientoReparacion[]>('/reparaciones/', { params });
  return res.data;
}

export async function createProcedimiento(data: {
  equipment_id: string;
  falla_id?: string;
  cotizacion_id?: string;
  descripcion?: string;
  tipo?: string;
  notas?: string;
}): Promise<ProcedimientoReparacion> {
  const res = await api.post<ProcedimientoReparacion>('/reparaciones/', data);
  return res.data;
}

export async function getProcedimiento(id: string): Promise<ProcedimientoReparacion> {
  const res = await api.get<ProcedimientoReparacion>(`/reparaciones/${id}`);
  return res.data;
}

export async function addPaso(procId: string, descripcion: string, tiempoMinutos: number): Promise<any> {
  const res = await api.post(`/reparaciones/${procId}/pasos`, {
    descripcion,
    tiempo_minutos: tiempoMinutos,
  });
  return res.data;
}

export async function uploadPasoFoto(procId: string, pasoId: string, file: File): Promise<any> {
  const formData = new FormData();
  formData.append('file', file);
  const res = await api.post(`/reparaciones/${procId}/pasos/${pasoId}/fotos`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return res.data;
}

export async function completarProcedimiento(procId: string, tiempoTotal: number, notas?: string): Promise<ProcedimientoReparacion> {
  const res = await api.patch(`/reparaciones/${procId}/completar`, {
    tiempo_total_horas: tiempoTotal,
    notas,
  });
  return res.data;
}

// --- Reportes ---
export async function generarReporte(fallaId: string): Promise<ReporteCliente> {
  const res = await api.post<ReporteCliente>(`/reportes/generar/${fallaId}`, {}, { timeout: 180000 });
  return res.data;
}

export async function getReporte(id: string): Promise<ReporteCliente> {
  const res = await api.get<ReporteCliente>(`/reportes/${id}`);
  return res.data;
}

export async function downloadReportePdf(id: string): Promise<void> {
  const blob = await fetchPdf(`/reportes/${id}/pdf`);
  openPdfInNewTab(blob, `reporte-${id}.pdf`);
}
