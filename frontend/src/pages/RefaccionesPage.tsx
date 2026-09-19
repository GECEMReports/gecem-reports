import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router';
import { useQuery, useMutation } from '@tanstack/react-query';
import { getFalla, sugerirRefacciones, confirmarRefacciones } from '@/api/falla';
import type { RefaccionSugerida, ConfirmarRefaccionItem } from '@/schemas/falla';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  ArrowLeft,
  Loader2,
  Check,
  Edit3,
  Plus,
  Trash2,
  Sparkles,
  AlertTriangle,
} from 'lucide-react';

const prioridadConfig: Record<string, { label: string; color: string }> = {
  urgente: { label: 'Urgente', color: 'bg-red-500/20 text-red-400 border-red-500/30' },
  normal: { label: 'Normal', color: 'bg-blue-500/20 text-blue-400 border-blue-500/30' },
  preventivo: { label: 'Preventivo', color: 'bg-green-500/20 text-green-400 border-green-500/30' },
};

type EditableRefaccion = RefaccionSugerida & { editing: boolean; originalPrecio: number | null };

export default function RefaccionesPage() {
  const { id: fallaId } = useParams<{ id: string }>();
  const [refacciones, setRefacciones] = useState<EditableRefaccion[]>([]);
  const [notas, setNotas] = useState('');
  const [saved, setSaved] = useState(false);

  const { data: falla } = useQuery({
    queryKey: ['falla', fallaId],
    queryFn: () => getFalla(fallaId!),
    enabled: !!fallaId,
  });

  const sugerirMutation = useMutation({
    mutationFn: () => sugerirRefacciones(fallaId!),
    onSuccess: (data) => {
      setNotas(data.notas);
      setRefacciones(
        data.refacciones.map((r) => ({
          ...r,
          editing: false,
          originalPrecio: r.precio_estimado ?? null,
        }))
      );
    },
  });

  const confirmarMutation = useMutation({
    mutationFn: async () => {
      const items: ConfirmarRefaccionItem[] = refacciones.map((r) => ({
        nombre: r.nombre,
        numero_parte: r.numero_parte || undefined,
        cantidad: r.cantidad,
        precio_unitario: r.precio_estimado ?? undefined,
        moneda: r.moneda,
        prioridad: r.prioridad,
        precio_confirmado: true,
        editado_por_mecanico: r.editado_por_mecanico,
      }));
      return confirmarRefacciones(fallaId!, items);
    },
    onSuccess: () => {
      setSaved(true);
    },
  });

  // Auto-suggest on load
  useEffect(() => {
    if (fallaId && refacciones.length === 0 && !sugerirMutation.isPending) {
      sugerirMutation.mutate();
    }
  }, [fallaId]);

  const updateRefaccion = (index: number, updates: Partial<EditableRefaccion>) => {
    setRefacciones((prev) =>
      prev.map((r, i) => {
        if (i !== index) return r;
        const updated = { ...r, ...updates };
        // Track if mechanic edited the price
        if (
          updates.precio_estimado !== undefined &&
          updates.precio_estimado !== r.originalPrecio
        ) {
          updated.editado_por_mecanico = true;
        }
        return updated;
      })
    );
  };

  const removeRefaccion = (index: number) => {
    setRefacciones((prev) => prev.filter((_, i) => i !== index));
  };

  const addEmptyRefaccion = () => {
    setRefacciones((prev) => [
      ...prev,
      {
        nombre: '',
        cantidad: 1,
        precio_estimado: null,
        moneda: 'MXN',
        prioridad: 'normal',
        precio_confirmado: false,
        editado_por_mecanico: true,
        editing: true,
        originalPrecio: null,
      },
    ]);
  };

  return (
    <div className="max-w-3xl space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Link to={`/fallas/${fallaId}`}>
          <Button variant="ghost" size="icon">
            <ArrowLeft className="h-5 w-5" />
          </Button>
        </Link>
        <div className="flex-1">
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <Sparkles className="h-6 w-6 text-yellow-500" />
            Refacciones sugeridas
          </h1>
          {falla && (
            <p className="text-zinc-400 text-sm">
              {falla.parte} — {falla.pieza}
            </p>
          )}
        </div>
      </div>

      {/* Loading */}
      {sugerirMutation.isPending && (
        <Card className="border-zinc-800 bg-zinc-900">
          <CardContent className="flex flex-col items-center justify-center py-12">
            <Loader2 className="h-12 w-12 text-yellow-500 animate-spin mb-4" />
            <p className="text-zinc-300 text-lg">Analizando falla y sugiriendo refacciones...</p>
            <p className="text-zinc-500 text-sm mt-1">Esto puede tomar hasta 2 minutos</p>
          </CardContent>
        </Card>
      )}

      {/* Error */}
      {sugerirMutation.isError && (
        <Card className="border-red-500/30 bg-red-950/20">
          <CardContent className="py-4">
            <p className="text-red-400">Error al sugerir refacciones. Intenta de nuevo.</p>
            <Button
              variant="outline"
              className="mt-3"
              onClick={() => sugerirMutation.mutate()}
            >
              Reintentar
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Saved confirmation */}
      {saved && (
        <Card className="border-green-500/30 bg-green-950/20">
          <CardContent className="py-4 flex items-center gap-3">
            <Check className="h-5 w-5 text-green-400" />
            <div>
              <p className="text-green-400 font-medium">Refacciones guardadas</p>
              <p className="text-zinc-400 text-sm">
                {refacciones.length} refacciones confirmadas para esta falla
              </p>
            </div>
            <Link to={`/fallas/${fallaId}`} className="ml-auto">
              <Button variant="outline" size="sm">Volver a falla</Button>
            </Link>
          </CardContent>
        </Card>
      )}

      {/* Refacciones list */}
      {refacciones.length > 0 && !saved && (
        <>
          {notas && (
            <Card className="border-zinc-800 bg-zinc-900">
              <CardContent className="py-3">
                <p className="text-xs text-zinc-500 mb-1">Notas del agente</p>
                <p className="text-sm text-zinc-300">{notas}</p>
              </CardContent>
            </Card>
          )}

          <div className="space-y-3">
            {refacciones.map((ref, index) => {
              const prioridad = prioridadConfig[ref.prioridad] || prioridadConfig.normal;
              return (
                <Card key={index} className="border-zinc-800 bg-zinc-900">
                  <CardContent className="py-4">
                    {ref.editing ? (
                      <div className="space-y-3">
                        <div className="grid grid-cols-2 gap-3">
                          <div>
                            <Label className="text-xs">Nombre</Label>
                            <Input
                              value={ref.nombre}
                              onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                                updateRefaccion(index, { nombre: e.target.value })
                              }
                              placeholder="Nombre de la refacción"
                            />
                          </div>
                          <div>
                            <Label className="text-xs">Número de parte</Label>
                            <Input
                              value={ref.numero_parte || ''}
                              onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                                updateRefaccion(index, { numero_parte: e.target.value })
                              }
                              placeholder="Opcional"
                            />
                          </div>
                        </div>
                        <div className="grid grid-cols-3 gap-3">
                          <div>
                            <Label className="text-xs">Cantidad</Label>
                            <Input
                              type="number"
                              value={ref.cantidad}
                              onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                                updateRefaccion(index, { cantidad: parseFloat(e.target.value) || 1 })
                              }
                            />
                          </div>
                          <div>
                            <Label className="text-xs">Precio unitario</Label>
                            <Input
                              type="number"
                              value={ref.precio_estimado ?? ''}
                              onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                                updateRefaccion(index, {
                                  precio_estimado: e.target.value ? parseFloat(e.target.value) : null,
                                })
                              }
                              placeholder="0"
                            />
                          </div>
                          <div>
                            <Label className="text-xs">Prioridad</Label>
                            <select
                              value={ref.prioridad}
                              onChange={(e) => updateRefaccion(index, { prioridad: e.target.value })}
                              className="w-full h-9 rounded-md border border-zinc-700 bg-zinc-800 px-3 text-sm text-white"
                            >
                              <option value="urgente">Urgente</option>
                              <option value="normal">Normal</option>
                              <option value="preventivo">Preventivo</option>
                            </select>
                          </div>
                        </div>
                        <div className="flex gap-2">
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => updateRefaccion(index, { editing: false })}
                          >
                            Listo
                          </Button>
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => removeRefaccion(index)}
                          >
                            <Trash2 className="h-4 w-4 mr-1" />
                            Eliminar
                          </Button>
                        </div>
                      </div>
                    ) : (
                      <div className="flex items-center justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <span className="text-white font-medium">{ref.nombre}</span>
                            <Badge variant="outline" className={prioridad.color}>
                              {prioridad.label}
                            </Badge>
                            {ref.editado_por_mecanico && (
                              <Badge variant="outline" className="bg-purple-500/20 text-purple-400 border-purple-500/30">
                                <Edit3 className="h-3 w-3 mr-1" />
                                Editado
                              </Badge>
                            )}
                          </div>
                          <div className="flex items-center gap-4 text-xs text-zinc-500">
                            {ref.numero_parte && (
                              <div className="flex items-center gap-1">
                                <span>P/N: {ref.numero_parte}</span>
                                <AlertTriangle className="h-3 w-3 text-yellow-500 flex-shrink-0" />
                                <span className="text-yellow-500 text-xs">Sugerido — verifica con proveedor</span>
                              </div>
                            )}
                            <span>x{ref.cantidad}</span>
                            <span>{ref.moneda}</span>
                          </div>
                        </div>
                        <div className="flex items-center gap-3">
                          <div className="text-right">
                            <p className="text-white font-medium">
                              {ref.precio_estimado
                                ? `$${ref.precio_estimado.toLocaleString()}`
                                : 'Sin precio'}
                            </p>
                            <p className="text-xs text-zinc-500">Estimado IA</p>
                          </div>
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => updateRefaccion(index, { editing: true })}
                          >
                            <Edit3 className="h-4 w-4" />
                          </Button>
                        </div>
                      </div>
                    )}
                  </CardContent>
                </Card>
              );
            })}
          </div>

          {/* Add button */}
          <Button variant="outline" onClick={addEmptyRefaccion} className="w-full">
            <Plus className="h-4 w-4 mr-2" />
            Agregar refacción manual
          </Button>

          {/* Confirm */}
          <Card className="border-zinc-800 bg-zinc-900">
            <CardContent className="py-4 flex items-center justify-between">
              <div>
                <p className="text-white font-medium">
                  {refacciones.length} refacciones listas
                </p>
                <p className="text-xs text-zinc-500">
                  {refacciones.filter((r) => r.editado_por_mecanico).length} editadas por ti ·{' '}
                  {refacciones.filter((r) => !r.editado_por_mecanico).length} precio IA sin cambios
                </p>
              </div>
              <Button
                onClick={() => confirmarMutation.mutate()}
                disabled={confirmarMutation.isPending}
              >
                {confirmarMutation.isPending ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Guardando...
                  </>
                ) : (
                  <>
                    <Check className="h-4 w-4 mr-2" />
                    Confirmar refacciones
                  </>
                )}
              </Button>
            </CardContent>
          </Card>
        </>
      )}

      {/* Back link */}
      <Link to={`/fallas/${fallaId}`}>
        <Button variant="ghost">Volver a falla</Button>
      </Link>
    </div>
  );
}
