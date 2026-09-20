import { useState } from 'react';
import { useParams, Link } from 'react-router';
import { useQuery, useMutation } from '@tanstack/react-query';
import {
  getFalla,
  createProcedimiento,
  getProcedimiento,
  addPaso,
  uploadPasoFoto,
  completarProcedimiento,
} from '@/api/falla';
import type { ProcedimientoReparacion } from '@/schemas/falla';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  ArrowLeft,
  Camera,
  Check,
  Clock,
  Loader2,
  Plus,
  Wrench,
} from 'lucide-react';

export default function ReparacionPage() {
  const { id: fallaId } = useParams<{ id: string }>();

  const [procedimiento, setProcedimiento] = useState<ProcedimientoReparacion | null>(null);
  const [pasoDesc, setPasoDesc] = useState('');
  const [pasoTiempo, setPasoTiempo] = useState<number>(0);
  const [tiempoTotal, setTiempoTotal] = useState<number>(0);
  const [notasFinales, setNotasFinales] = useState('');
  const [completado, setCompletado] = useState(false);

  const { data: falla } = useQuery({
    queryKey: ['falla', fallaId],
    queryFn: () => getFalla(fallaId!),
    enabled: !!fallaId,
  });

  const crearMutation = useMutation({
    mutationFn: () => createProcedimiento(fallaId!),
    onSuccess: (proc) => {
      setProcedimiento(proc);
    },
  });

  const addPasoMutation = useMutation({
    mutationFn: () => addPaso(procedimiento!.id, pasoDesc, pasoTiempo),
    onSuccess: () => {
      setPasoDesc('');
      setPasoTiempo(0);
      // Refresh procedimiento
      getProcedimiento(procedimiento!.id).then(setProcedimiento);
    },
  });

  const uploadFotoMutation = useMutation({
    mutationFn: async ({ pasoId, file }: { pasoId: string; file: File }) => {
      return uploadPasoFoto(procedimiento!.id, pasoId, file);
    },
    onSuccess: () => {
      getProcedimiento(procedimiento!.id).then(setProcedimiento);
    },
  });

  const completarMutation = useMutation({
    mutationFn: () => completarProcedimiento(procedimiento!.id, tiempoTotal, notasFinales),
    onSuccess: (proc) => {
      setProcedimiento(proc);
      setCompletado(true);
    },
  });

  return (
    <div className="max-w-3xl space-y-6">
      <div className="flex items-center gap-4">
        <Link to={`/fallas/${fallaId}`}>
          <Button variant="ghost" size="icon">
            <ArrowLeft className="h-5 w-5" />
          </Button>
        </Link>
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <Wrench className="h-6 w-6 text-yellow-500" />
            Reparación
          </h1>
          {falla && (
            <p className="text-zinc-400 text-sm">{falla.parte} — {falla.pieza}</p>
          )}
        </div>
      </div>

      {/* Create or show procedure */}
      {!procedimiento && !completado && (
        <Card className="border-zinc-800 bg-zinc-900">
          <CardContent className="py-8 text-center">
            <p className="text-zinc-400 mb-4">Inicia el registro de la reparación</p>
            <Button onClick={() => crearMutation.mutate()} disabled={crearMutation.isPending}>
              {crearMutation.isPending ? (
                <><Loader2 className="h-4 w-4 mr-2 animate-spin" /> Creando...</>
              ) : (
                <><Plus className="h-4 w-4 mr-2" /> Iniciar reparación</>
              )}
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Steps */}
      {procedimiento && !completado && (
        <>
          {/* Existing steps */}
          {procedimiento.pasos.length > 0 && (
            <Card className="border-zinc-800 bg-zinc-900">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm text-zinc-400">
                  Pasos ({procedimiento.pasos.length})
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {procedimiento.pasos.map((paso) => (
                  <div key={paso.id} className="p-3 rounded-lg bg-zinc-800/50 border border-zinc-700">
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <Badge variant="outline" className="bg-zinc-700 text-zinc-300">
                          Paso {paso.numero_paso}
                        </Badge>
                        <span className="text-sm text-zinc-400">
                          <Clock className="h-3 w-3 inline mr-1" />
                          {paso.tiempo_minutos} min
                        </span>
                      </div>
                      <label className="cursor-pointer">
                        <input
                          type="file"
                          accept="image/*"
                          capture="environment"
                          className="hidden"
                          onChange={(e) => {
                            const file = e.target.files?.[0];
                            if (file) uploadFotoMutation.mutate({ pasoId: paso.id, file });
                          }}
                        />
                        <Camera className="h-4 w-4 text-zinc-400 hover:text-white" />
                      </label>
                    </div>
                    <p className="text-white text-sm">{paso.descripcion}</p>
                    {paso.fotos.length > 0 && (
                      <div className="flex gap-2 mt-2">
                        {paso.fotos.map((foto) => (
                          <div key={foto.id} className="w-16 h-16 rounded bg-zinc-700 overflow-hidden">
                            <img
                              src={`/api/reparaciones/fotos/${foto.filename}`}
                              alt="Foto"
                              className="w-full h-full object-cover"
                              onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
                            />
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </CardContent>
            </Card>
          )}

          {/* Add step */}
          <Card className="border-zinc-800 bg-zinc-900">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm text-zinc-400">Agregar paso</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                <div>
                  <Label>Descripción del paso</Label>
                  <Textarea
                    value={pasoDesc}
                    onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setPasoDesc(e.target.value)}
                    placeholder="Describir qué se hizo en este paso..."
                    rows={2}
                  />
                </div>
                <div className="flex gap-3 items-end">
                  <div className="flex-1">
                    <Label>Tiempo (minutos)</Label>
                    <Input
                      type="number"
                      value={pasoTiempo || ''}
                      onChange={(e: React.ChangeEvent<HTMLInputElement>) => setPasoTiempo(parseFloat(e.target.value) || 0)}
                      placeholder="0"
                    />
                  </div>
                  <Button
                    onClick={() => addPasoMutation.mutate()}
                    disabled={!pasoDesc.trim() || addPasoMutation.isPending}
                  >
                    <Plus className="h-4 w-4 mr-1" />
                    Agregar
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Complete */}
          <Card className="border-zinc-800 bg-zinc-900">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm text-zinc-400">Completar reparación</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                <div>
                  <Label>Tiempo total real (horas)</Label>
                  <Input
                    type="number"
                    step="0.5"
                    value={tiempoTotal || ''}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => setTiempoTotal(parseFloat(e.target.value) || 0)}
                    placeholder="0"
                  />
                </div>
                <div>
                  <Label>Notas finales (opcional)</Label>
                  <Textarea
                    value={notasFinales}
                    onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setNotasFinales(e.target.value)}
                    placeholder="Observaciones, recomendaciones..."
                    rows={2}
                  />
                </div>
                <Button
                  onClick={() => completarMutation.mutate()}
                  disabled={procedimiento.pasos.length === 0 || tiempoTotal <= 0 || completarMutation.isPending}
                  className="w-full"
                >
                  {completarMutation.isPending ? (
                    <><Loader2 className="h-4 w-4 mr-2 animate-spin" /> Completando...</>
                  ) : (
                    <><Check className="h-4 w-4 mr-2" /> Marcar como completada</>
                  )}
                </Button>
              </div>
            </CardContent>
          </Card>
        </>
      )}

      {/* Completed */}
      {completado && (
        <Card className="border-green-500/30 bg-green-950/20">
          <CardContent className="py-6 text-center">
            <Check className="h-12 w-12 text-green-400 mx-auto mb-3" />
            <p className="text-green-400 text-lg font-medium">Reparación completada</p>
            <p className="text-zinc-400 text-sm mt-1">
              {procedimiento?.pasos.length} pasos · {tiempoTotal} horas
            </p>
            <div className="flex gap-3 justify-center mt-4">
              <Link to={`/fallas/${fallaId}/reporte`}>
                <Button>Generar reporte para cliente</Button>
              </Link>
              <Link to={`/fallas/${fallaId}`}>
                <Button variant="outline">Volver a falla</Button>
              </Link>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
