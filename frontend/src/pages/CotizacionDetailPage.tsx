import { useQuery } from '@tanstack/react-query';
import { useParams, Link } from 'react-router';
import { getCotizacion, getCotizacionPdfUrl, listRefacciones } from '@/api/falla';
import { getEquipment } from '@/api/equipment';
import { getFalla } from '@/api/falla';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  ArrowLeft,
  Calculator,
  Download,
  FileText,
  Package,
  Truck,
} from 'lucide-react';

const statusConfig: Record<string, { label: string; color: string }> = {
  borrador: { label: 'Borrador', color: 'bg-zinc-500/20 text-zinc-400 border-zinc-500/30' },
  enviada: { label: 'Enviada', color: 'bg-blue-500/20 text-blue-400 border-blue-500/30' },
  aprobada: { label: 'Aprobada', color: 'bg-green-500/20 text-green-400 border-green-500/30' },
  rechazada: { label: 'Rechazada', color: 'bg-red-500/20 text-red-400 border-red-500/30' },
};

export default function CotizacionDetailPage() {
  const { id } = useParams<{ id: string }>();

  const { data: cotizacion, isLoading } = useQuery({
    queryKey: ['cotizacion', id],
    queryFn: () => getCotizacion(id!),
    enabled: !!id,
  });

  const { data: falla } = useQuery({
    queryKey: ['falla', cotizacion?.falla_id],
    queryFn: () => getFalla(cotizacion!.falla_id),
    enabled: !!cotizacion?.falla_id,
  });

  const { data: equipment } = useQuery({
    queryKey: ['equipment', 'detail', cotizacion?.equipment_id],
    queryFn: () => getEquipment(cotizacion!.equipment_id),
    enabled: !!cotizacion?.equipment_id,
  });

  const { data: refacciones } = useQuery({
    queryKey: ['refacciones', 'list', cotizacion?.falla_id],
    queryFn: () => listRefacciones(cotizacion!.falla_id),
    enabled: !!cotizacion?.falla_id,
  });

  if (isLoading) {
    return <div className="text-zinc-400">Cargando cotizacion...</div>;
  }

  if (!cotizacion) {
    return (
      <div className="text-center py-12">
        <p className="text-zinc-400 mb-4">Cotizacion no encontrada</p>
        <Link to="/fallas">
          <Button variant="outline">Volver a fallas</Button>
        </Link>
      </div>
    );
  }

  const status = statusConfig[cotizacion.status] || statusConfig.borrador;

  return (
    <div className="max-w-3xl space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Link to={`/fallas/${cotizacion.falla_id}`}>
          <Button variant="ghost" size="icon">
            <ArrowLeft className="h-5 w-5" />
          </Button>
        </Link>
        <div className="flex-1">
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <FileText className="h-6 w-6 text-yellow-500" />
            Cotización
          </h1>
          {falla && (
            <p className="text-zinc-400 text-sm">
              {falla.parte} — {falla.pieza}
            </p>
          )}
        </div>
        <div className="flex flex-col items-end gap-2">
          <Badge variant="outline" className={status.color}>
            {status.label}
          </Badge>
          {cotizacion.fecha_vencimiento && (
            <p className="text-xs text-zinc-500">
              Válida hasta: {new Date(cotizacion.fecha_vencimiento).toLocaleDateString('es-MX')}
            </p>
          )}
        </div>
      </div>

      {/* Equipment */}
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

      {/* Refacciones */}
      <Card className="border-zinc-800 bg-zinc-900">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm text-zinc-400 flex items-center gap-2">
            <Package className="h-4 w-4" />
            Refacciones ({refacciones?.length ?? 0})
          </CardTitle>
        </CardHeader>
        <CardContent>
          {refacciones && refacciones.length > 0 ? (
            <div className="space-y-2">
              {refacciones.map((ref) => (
                <div
                  key={ref.id}
                  className="flex items-center justify-between p-2 rounded bg-zinc-800/50"
                >
                  <div>
                    <p className="text-white text-sm">{ref.nombre}</p>
                    <p className="text-zinc-500 text-xs">x{ref.cantidad}</p>
                  </div>
                  <p className="text-white text-sm">
                    ${((ref.precio_unitario || 0) * ref.cantidad).toLocaleString()} {ref.moneda}
                  </p>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-zinc-500 text-sm">Sin refacciones</p>
          )}
        </CardContent>
      </Card>

      {/* Totals */}
      <Card className="border-zinc-800 bg-zinc-900">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm text-zinc-400 flex items-center gap-2">
            <Calculator className="h-4 w-4" />
            Resumen
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <p className="text-zinc-400">Refacciones</p>
              <p className="text-white">${cotizacion.subtotal_refacciones.toLocaleString()} {cotizacion.moneda}</p>
            </div>
            <div className="flex justify-between text-sm">
              <p className="text-zinc-400">Mano de obra</p>
              <p className="text-white">${cotizacion.mano_de_obra.toLocaleString()} {cotizacion.moneda}</p>
            </div>
            <div className="flex justify-between text-sm">
              <p className="text-zinc-400">IVA</p>
              <p className="text-zinc-500">Incluido</p>
            </div>
            <div className="flex justify-between pt-2 border-t border-zinc-700">
              <p className="text-lg text-white font-medium">Total</p>
              <p className="text-lg text-white font-bold">${cotizacion.total.toLocaleString()} {cotizacion.moneda}</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Notas */}
      {cotizacion.notas && (
        <Card className="border-zinc-800 bg-zinc-900">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm text-zinc-400">Notas</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-zinc-300 text-sm">{cotizacion.notas}</p>
          </CardContent>
        </Card>
      )}

      {/* Actions */}
      <div className="flex gap-3">
        <a href={getCotizacionPdfUrl(cotizacion.id)} target="_blank" rel="noopener noreferrer">
          <Button>
            <Download className="h-4 w-4 mr-2" />
            Descargar PDF
          </Button>
        </a>
        <Link to={`/fallas/${cotizacion.falla_id}`}>
          <Button variant="outline">Volver a falla</Button>
        </Link>
      </div>
    </div>
  );
}
