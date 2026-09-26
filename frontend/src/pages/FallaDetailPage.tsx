import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useParams, Link } from 'react-router';
import { getFalla, listRefacciones } from '@/api/falla';
import { getEquipment } from '@/api/equipment';
import api, { getApiUrl } from '@/api/client';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import {
  ArrowLeft,
  AlertTriangle,
  Calculator,
  Camera,
  FileText,
  Package,
  Sparkles,
  Truck,
  Check,
  Wrench,
} from 'lucide-react';

const prioridadConfig: Record<string, { label: string; color: string }> = {
  baja: { label: 'Baja', color: 'bg-green-500/20 text-green-400 border-green-500/30' },
  normal: { label: 'Normal', color: 'bg-blue-500/20 text-blue-400 border-blue-500/30' },
  urgente: { label: 'Urgente', color: 'bg-orange-500/20 text-orange-400 border-orange-500/30' },
  critica: { label: 'Crítica', color: 'bg-red-500/20 text-red-400 border-red-500/30' },
};

const statusConfig: Record<string, { label: string; color: string }> = {
  detectada: { label: 'Detectada', color: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30' },
  en_reparacion: { label: 'En reparación', color: 'bg-blue-500/20 text-blue-400 border-blue-500/30' },
  terminada: { label: 'Terminada', color: 'bg-green-500/20 text-green-400 border-green-500/30' },
};

export default function FallaDetailPage() {
  const { id } = useParams<{ id: string }>();
  const queryClient = useQueryClient();

  const { data: falla, isLoading } = useQuery({
    queryKey: ['falla', id],
    queryFn: () => getFalla(id!),
    enabled: !!id,
  });

  const { data: refacciones } = useQuery({
    queryKey: ['refacciones', id],
    queryFn: () => listRefacciones(id!),
    enabled: !!id,
  });

  const { data: equipment } = useQuery({
    queryKey: ['equipment', 'detail', falla?.equipment_id],
    queryFn: () => getEquipment(falla!.equipment_id),
    enabled: !!falla?.equipment_id,
  });

  const statusMutation = useMutation({
    mutationFn: async (newStatus: string) => {
      await api.patch(`/fallas/${id}`, { status: newStatus });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['falla', id] });
      queryClient.invalidateQueries({ queryKey: ['fallas'] });
    },
  });

  if (isLoading) {
    return <div className="text-zinc-400">Cargando falla...</div>;
  }

  if (!falla) {
    return (
      <div className="text-center py-12">
        <p className="text-zinc-400 mb-4">Falla no encontrada</p>
        <Link to="/fallas">
          <Button variant="outline">Volver a fallas</Button>
        </Link>
      </div>
    );
  }

  const prioridad = prioridadConfig[falla.prioridad] || prioridadConfig.normal;
  const status = statusConfig[falla.status] || statusConfig.detectada;

  const nextStatus: Record<string, string> = {
    detectada: 'en_reparacion',
    en_reparacion: 'terminada',
  };

  const nextStatusLabel: Record<string, string> = {
    detectada: 'Iniciar reparación',
    en_reparacion: 'Marcar terminada',
  };

  return (
    <div className="max-w-3xl space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Link to="/fallas">
          <Button variant="ghost" size="icon">
            <ArrowLeft className="h-5 w-5" />
          </Button>
        </Link>
        <div className="flex-1">
          <h1 className="text-2xl font-bold text-white">
            {falla.parte} — {falla.pieza}
          </h1>
          <p className="text-zinc-400 text-sm">
            {equipment ? `${equipment.brand} ${equipment.model}` : 'Equipo'} ·{' '}
            {new Date(falla.created_at).toLocaleDateString('es-MX')}
          </p>
        </div>
        <div className="flex gap-2">
          <Badge variant="outline" className={prioridad.color}>
            <AlertTriangle className="h-3 w-3 mr-1" />
            {prioridad.label}
          </Badge>
          <Badge variant="outline" className={status.color}>
            {status.label}
          </Badge>
        </div>
      </div>

      {/* Status action */}
      {nextStatus[falla.status] && (
        <Card className="border-zinc-800 bg-zinc-900">
          <CardContent className="py-4 flex items-center justify-between">
            <p className="text-sm text-zinc-400">
              Status actual: <span className="text-white font-medium">{status.label}</span>
            </p>
            <Button
              size="sm"
              onClick={() => statusMutation.mutate(nextStatus[falla.status])}
              disabled={statusMutation.isPending}
            >
              <Check className="h-4 w-4 mr-1" />
              {statusMutation.isPending ? 'Actualizando...' : nextStatusLabel[falla.status]}
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Equipment info */}
      {equipment && (
        <Card className="border-zinc-800 bg-zinc-900">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm text-zinc-400 flex items-center gap-2">
              <Truck className="h-4 w-4" />
              Equipo
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-3 gap-4 text-sm">
              <div>
                <p className="text-zinc-500">Marca/Modelo</p>
                <p className="text-white">{equipment.brand} {equipment.model}</p>
              </div>
              <div>
                <p className="text-zinc-500">Serie</p>
                <p className="text-white">{equipment.serial_number}</p>
              </div>
              <div>
                <p className="text-zinc-500">Horas</p>
                <p className="text-white">{equipment.hours.toLocaleString()}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Descripción */}
      <Card className="border-zinc-800 bg-zinc-900">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm text-zinc-400 flex items-center gap-2">
            <Wrench className="h-4 w-4" />
            Descripción de la falla
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-zinc-300 text-sm whitespace-pre-wrap">{falla.descripcion}</p>
          {falla.causa_raiz && (
            <>
              <Separator className="bg-zinc-800 my-3" />
              <p className="text-xs text-zinc-500 mb-1">Causa raíz</p>
              <p className="text-zinc-300 text-sm">{falla.causa_raiz}</p>
            </>
          )}
          {falla.notas && (
            <>
              <Separator className="bg-zinc-800 my-3" />
              <p className="text-xs text-zinc-500 mb-1">Notas</p>
              <p className="text-zinc-300 text-sm">{falla.notas}</p>
            </>
          )}
        </CardContent>
      </Card>

      {/* Fotos */}
      <Card className="border-zinc-800 bg-zinc-900">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm text-zinc-400 flex items-center gap-2">
            <Camera className="h-4 w-4" />
            Evidencia fotográfica ({falla.fotos.length})
          </CardTitle>
        </CardHeader>
        <CardContent>
          {falla.fotos.length === 0 ? (
            <p className="text-zinc-500 text-sm">No hay fotos adjuntas</p>
          ) : (
            <div className="grid grid-cols-3 gap-3">
              {falla.fotos.map((foto) => (
                <div
                  key={foto.id}
                  className="aspect-square rounded-lg bg-zinc-800 overflow-hidden border border-zinc-700"
                >
                  <img
                    src={getApiUrl(`/api/fallas/fotos/${foto.filename}`)}
                    alt={foto.descripcion || 'Foto de falla'}
                    className="w-full h-full object-cover"
                    onError={(e) => {
                      (e.target as HTMLImageElement).style.display = 'none';
                    }}
                  />
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Refacciones */}
      <Card className="border-zinc-800 bg-zinc-900">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm text-zinc-400 flex items-center gap-2">
            <Package className="h-4 w-4" />
            Refacciones ({refacciones?.length ?? 0})
          </CardTitle>
        </CardHeader>
        <CardContent>
          {!refacciones || refacciones.length === 0 ? (
            <div className="text-center py-4">
              <p className="text-zinc-500 text-sm mb-3">No hay refacciones registradas</p>
              <Link to={`/fallas/${id}/refacciones`}>
                <Button size="sm">
                  <Sparkles className="h-4 w-4 mr-2" />
                  Sugerir con IA
                </Button>
              </Link>
            </div>
          ) : (
            <div className="space-y-2">
              {refacciones.map((ref) => (
                <div
                  key={ref.id}
                  className="flex items-center justify-between p-3 rounded-lg bg-zinc-800/50 border border-zinc-700"
                >
                  <div>
                    <p className="text-white text-sm font-medium">{ref.nombre}</p>
                    {ref.numero_parte && (
                      <p className="text-zinc-500 text-xs">P/N: {ref.numero_parte}</p>
                    )}
                  </div>
                  <div className="text-right">
                    <p className="text-white text-sm">
                      {ref.precio_unitario
                        ? `$${ref.precio_unitario.toLocaleString()} ${ref.moneda}`
                        : 'Sin precio'}
                    </p>
                    <p className="text-zinc-500 text-xs">x{ref.cantidad}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Actions */}
      <div className="flex gap-3 flex-wrap">
        <Link to={`/fallas/${id}/cotizacion`}>
          <Button>
            <Calculator className="h-4 w-4 mr-2" />
            Cotizar
          </Button>
        </Link>
        <Link to={`/fallas/${id}/reporte`}>
          <Button variant="outline">
            <FileText className="h-4 w-4 mr-2" />
            Reporte cliente
          </Button>
        </Link>
        <Link to="/fallas">
          <Button variant="ghost">Volver a fallas</Button>
        </Link>
        <Link to={`/diagnosis`}>
          <Button variant="ghost">Nuevo diagnostico</Button>
        </Link>
      </div>
    </div>
  );
}
