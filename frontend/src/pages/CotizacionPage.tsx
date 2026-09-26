import { useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router';
import { useQuery, useMutation } from '@tanstack/react-query';
import { getFalla, listRefacciones, createCotizacionManual } from '@/api/falla';
import { listEquipment } from '@/api/equipment';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  ArrowLeft,
  Calculator,
  DollarSign,
  Loader2,
} from 'lucide-react';

export default function CotizacionPage() {
  const { id: fallaId } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [manoDeObra, setManoDeObra] = useState<number>(0);
  const [notas, setNotas] = useState('');

  const { data: falla } = useQuery({
    queryKey: ['falla', fallaId],
    queryFn: () => getFalla(fallaId!),
    enabled: !!fallaId,
  });

  const { data: refacciones } = useQuery({
    queryKey: ['refacciones', fallaId],
    queryFn: () => listRefacciones(fallaId!),
    enabled: !!fallaId,
  });

  const { data: equipment } = useQuery({
    queryKey: ['equipment', 'list'],
    queryFn: listEquipment,
  });

  const subtotalRefacciones = refacciones?.reduce(
    (sum, r) => sum + (r.precio_unitario || 0) * r.cantidad,
    0
  ) ?? 0;

  const total = subtotalRefacciones + manoDeObra;

  const createMutation = useMutation({
    mutationFn: () =>
      createCotizacionManual({
        falla_id: fallaId!,
        subtotal_refacciones: subtotalRefacciones,
        mano_de_obra: manoDeObra,
        notas: notas || undefined,
      }),
    onSuccess: (cotizacion) => {
      navigate(`/cotizaciones/${cotizacion.id}`);
    },
  });

  const eq = equipment?.find((e) => e.id === falla?.equipment_id);

  return (
    <div className="max-w-2xl space-y-6">
      <div className="flex items-center gap-4">
        <Link to={`/fallas/${fallaId}`}>
          <Button variant="ghost" size="icon">
            <ArrowLeft className="h-5 w-5" />
          </Button>
        </Link>
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <Calculator className="h-6 w-6 text-yellow-500" />
            Cotización
          </h1>
          {falla && (
            <p className="text-zinc-400 text-sm">
              {falla.parte} — {falla.pieza}
            </p>
          )}
        </div>
      </div>

      {/* Equipment */}
      {eq && (
        <Card className="border-zinc-800 bg-zinc-900">
          <CardContent className="py-3 text-sm text-zinc-400">
            Equipo: {eq.brand} {eq.model} — {eq.serial_number}
          </CardContent>
        </Card>
      )}

      {/* Refacciones */}
      <Card className="border-zinc-800 bg-zinc-900">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm text-zinc-400">
            Refacciones ({refacciones?.length ?? 0})
          </CardTitle>
        </CardHeader>
        <CardContent>
          {!refacciones || refacciones.length === 0 ? (
            <div className="text-center py-4">
              <p className="text-zinc-500 text-sm mb-3">No hay refacciones registradas</p>
              <Link to={`/fallas/${fallaId}/refacciones`}>
                <Button size="sm" variant="outline">Agregar refacciones primero</Button>
              </Link>
            </div>
          ) : (
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
              <div className="flex items-center justify-between pt-2 border-t border-zinc-700">
                <p className="text-zinc-400 text-sm">Subtotal refacciones</p>
                <p className="text-white font-medium">${subtotalRefacciones.toLocaleString()} MXN</p>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Mano de obra + total */}
      <Card className="border-zinc-800 bg-zinc-900">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm text-zinc-400 flex items-center gap-2">
            <DollarSign className="h-4 w-4" />
            Mano de obra y total
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="mano_de_obra">Costo de mano de obra (MXN)</Label>
            <Input
              id="mano_de_obra"
              type="number"
              value={manoDeObra || ''}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                setManoDeObra(parseFloat(e.target.value) || 0)
              }
              placeholder="0"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="notas">Notas (opcional)</Label>
            <Textarea
              id="notas"
              value={notas}
              onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setNotas(e.target.value)}
              placeholder="Condiciones, garantía, observaciones..."
              rows={3}
            />
          </div>
          <div className="flex items-center justify-between pt-4 border-t border-zinc-700">
            <p className="text-lg text-zinc-300 font-medium">Total</p>
            <p className="text-2xl text-white font-bold">${total.toLocaleString()} MXN</p>
          </div>
        </CardContent>
      </Card>

      {/* Actions */}
      <div className="flex gap-3">
        <Button
          onClick={() => createMutation.mutate()}
          disabled={createMutation.isPending || subtotalRefacciones === 0}
          className="flex-1"
        >
          {createMutation.isPending ? (
            <>
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              Guardando...
            </>
          ) : (
            'Guardar cotización'
          )}
        </Button>
        <Link to={`/fallas/${fallaId}`}>
          <Button variant="outline">Cancelar</Button>
        </Link>
      </div>
    </div>
  );
}
