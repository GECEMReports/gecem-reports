import { useState } from 'react';
import { useParams, Link } from 'react-router';
import { useQuery, useMutation } from '@tanstack/react-query';
import { getProcedimiento, addPaso, uploadPasoFoto, completarProcedimiento } from '@/api/falla';
import { listEquipment } from '@/api/equipment';
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
  Truck,
  Wrench,
} from 'lucide-react';

const tipoConfig: Record<string, { label: string; color: string }> = {
  preventiva: { label: 'Preventiva', color: 'bg-green-500/20 text-green-400 border-green-500/30' },
  correctiva: { label: 'Correctiva', color: 'bg-blue-500/20 text-blue-400 border-blue-500/30' },
  emergencia: { label: 'Emergencia', color: 'bg-red-500/20 text-red-400 border-red-500/30' },
};

export default function ReparacionDetailPage() {
  const { id } = useParams<{ id: string }>();

  const [pasoDesc, setPasoDesc] = useState('');
  const [pasoTiempo, setPasoTiempo] = useState<number>(0);
  const [tiempoTotal, setTiempoTotal] = useState<number>(0);
  const [notasFinales, setNotasFinales] = useState('');
  const [completado, setCompletado] = useState(false);

  const { data: proc, refetch } = useQuery({
    queryKey: ['procedimiento', id],
    queryFn: () => getProcedimiento(id!),
    enabled: !!id,
  });

  const { data: equipment } = useQuery({
    queryKey: ['equipment'],
    queryFn: listEquipment,
  });

  const eq = equipment?.find((e) => e.id === proc?.equipment_id);
  const tipo = tipoConfig[proc?.tipo || 'correctiva'] || tipoConfig.correctiva;

  const addPasoMutation = useMutation({
    mutationFn: () => addPaso(id!, pasoDesc, pasoTiempo),
    onSuccess: () => {
      setPasoDesc('');
      setPasoTiempo(0);
      refetch();
    },
  });

  const uploadFotoMutation = useMutation({
    mutationFn: async ({ pasoId, file }: { pasoId: string; file: File }) => {
      return uploadPasoFoto(id!, pasoId, file);
    },
    onSuccess: () => refetch(),
  });

  const completarMutation = useMutation({
    mutationFn: () => completarProcedimiento(id!, tiempoTotal, notasFinales),
    onSuccess: () => {
      refetch();
      setCompletado(true);
    },
  });

  if (!proc) {
    return <div className="text-zinc-400">Cargando reparacion...</div>;
  }

  return (
    <div className="max-w-3xl space-y-6">
      <div className="flex items-center gap-4">
        <Link to="/reparaciones">
          <Button variant="ghost" size="icon">
            <ArrowLeft className="h-5 w-5" />
          </Button>
        </Link>
        <div className="flex-1">
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <Wrench className="h-6 w-6 text-yellow-500" />
            Reparacion
          </h1>
          <p className="text-zinc-400 text-sm">{proc.descripcion || 'Sin descripcion'}</p>
        </div>
        <Badge variant="outline" className={tipo.color}>{tipo.label}</Badge>
      </div>

      {/* Equipment info */}
      {eq && (
        <Card className="border-zinc-800 bg-zinc-900">
          <CardContent className="py-3 flex items-center gap-3 text-sm text-zinc-400">
            <Truck className="h-4 w-4" />
            {eq.brand} {eq.model} — {eq.serial_number}
          </CardContent>
        </Card>
      )}

      {/* Steps */}
      {proc.pasos.length > 0 && (
        <Card className="border-zinc-800 bg-zinc-900">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm text-zinc-400">Pasos ({proc.pasos.length})</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {proc.pasos.map((paso) => (
              <div key={paso.id} className="p-3 rounded-lg bg-zinc-800/50 border border-zinc-700">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <Badge variant="outline" className="bg-zinc-700 text-zinc-300">Paso {paso.numero_paso}</Badge>
                    <span className="text-sm text-zinc-400"><Clock className="h-3 w-3 inline mr-1" />{paso.tiempo_minutos} min</span>
                  </div>
                  {proc.status === 'en_progreso' && (
                    <label className="cursor-pointer">
                      <input type="file" accept="image/*" capture="environment" className="hidden"
                        onChange={(e) => { const f = e.target.files?.[0]; if (f) uploadFotoMutation.mutate({ pasoId: paso.id, file: f }); }} />
                      <Camera className="h-4 w-4 text-zinc-400 hover:text-white" />
                    </label>
                  )}
                </div>
                <p className="text-white text-sm">{paso.descripcion}</p>
                {paso.fotos.length > 0 && (
                  <div className="flex gap-2 mt-2">
                    {paso.fotos.map((foto) => (
                      <div key={foto.id} className="w-16 h-16 rounded bg-zinc-700 overflow-hidden">
                        <img src={`/api/reparaciones/fotos/${foto.filename}`} alt="" className="w-full h-full object-cover"
                          onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }} />
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {/* Add step (only if in progress) */}
      {proc.status === 'en_progreso' && (
        <Card className="border-zinc-800 bg-zinc-900">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm text-zinc-400">Agregar paso</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div>
                <Label>Descripcion</Label>
                <Textarea value={pasoDesc} onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setPasoDesc(e.target.value)} placeholder="Que se hizo..." rows={2} />
              </div>
              <div className="flex gap-3 items-end">
                <div className="flex-1">
                  <Label>Tiempo (min)</Label>
                  <Input type="number" value={pasoTiempo || ''} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setPasoTiempo(parseFloat(e.target.value) || 0)} />
                </div>
                <Button onClick={() => addPasoMutation.mutate()} disabled={!pasoDesc.trim() || addPasoMutation.isPending}>
                  <Plus className="h-4 w-4 mr-1" />Agregar
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Complete */}
      {proc.status === 'en_progreso' && (
        <Card className="border-zinc-800 bg-zinc-900">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm text-zinc-400">Completar reparacion</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div>
                <Label>Tiempo total real (horas)</Label>
                <Input type="number" step="0.5" value={tiempoTotal || ''} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setTiempoTotal(parseFloat(e.target.value) || 0)} />
              </div>
              <div>
                <Label>Notas finales</Label>
                <Textarea value={notasFinales} onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setNotasFinales(e.target.value)} rows={2} />
              </div>
              <Button onClick={() => completarMutation.mutate()} disabled={proc.pasos.length === 0 || tiempoTotal <= 0 || completarMutation.isPending} className="w-full">
                {completarMutation.isPending ? <><Loader2 className="h-4 w-4 mr-2 animate-spin" /> Completando...</> : <><Check className="h-4 w-4 mr-2" /> Marcar completada</>}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Completed */}
      {(proc.status === 'completado' || completado) && (
        <Card className="border-green-500/30 bg-green-950/20">
          <CardContent className="py-6 text-center">
            <Check className="h-12 w-12 text-green-400 mx-auto mb-3" />
            <p className="text-green-400 text-lg font-medium">Reparacion completada</p>
            <p className="text-zinc-400 text-sm mt-1">{proc.pasos.length} pasos · {proc.tiempo_total_horas} horas</p>
            <div className="flex gap-3 justify-center mt-4">
              {proc.falla_id && (
                <Link to={`/fallas/${proc.falla_id}/reporte`}>
                  <Button>Generar reporte cliente</Button>
                </Link>
              )}
              <Link to="/reparaciones">
                <Button variant="outline">Volver a reparaciones</Button>
              </Link>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
