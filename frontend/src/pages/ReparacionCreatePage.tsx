import { useState } from 'react';
import { useNavigate, Link } from 'react-router';
import { useQuery, useMutation } from '@tanstack/react-query';
import { listEquipment } from '@/api/equipment';
import { listFallas, createProcedimiento } from '@/api/falla';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ArrowLeft, Loader2, Wrench } from 'lucide-react';

export default function ReparacionCreatePage() {
  const navigate = useNavigate();
  const [equipmentId, setEquipmentId] = useState('');
  const [fallaId, setFallaId] = useState('');
  const [descripcion, setDescripcion] = useState('');
  const [tipo, setTipo] = useState('correctiva');
  const [notas, setNotas] = useState('');

  const { data: equipment } = useQuery({
    queryKey: ['equipment', 'list'],
    queryFn: listEquipment,
  });

  const { data: fallas } = useQuery({
    queryKey: ['fallas', equipmentId],
    queryFn: () => listFallas(equipmentId || undefined),
    enabled: !!equipmentId,
  });

  const createMutation = useMutation({
    mutationFn: () =>
      createProcedimiento({
        equipment_id: equipmentId,
        falla_id: fallaId || undefined,
        descripcion,
        tipo,
        notas: notas || undefined,
      }),
    onSuccess: (proc) => {
      navigate(`/reparaciones/${proc.id}`);
    },
  });

  return (
    <div className="max-w-2xl space-y-6">
      <div className="flex items-center gap-4">
        <Link to="/reparaciones">
          <Button variant="ghost" size="icon">
            <ArrowLeft className="h-5 w-5" />
          </Button>
        </Link>
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <Wrench className="h-6 w-6 text-yellow-500" />
            Nueva reparación
          </h1>
          <p className="text-zinc-400 text-sm">Registra un trabajo realizado</p>
        </div>
      </div>

      <Card className="border-zinc-800 bg-zinc-900">
        <CardHeader>
          <CardTitle className="text-white">Datos de la reparación</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={(e) => { e.preventDefault(); createMutation.mutate(); }} className="space-y-4">
            {createMutation.isError && (
              <div className="text-red-400 text-sm bg-red-950/50 p-2 rounded">
                Error al crear reparación
              </div>
            )}

            <div className="space-y-2">
              <Label>Equipo *</Label>
              <select
                value={equipmentId}
                onChange={(e) => { setEquipmentId(e.target.value); setFallaId(''); }}
                className="w-full h-10 rounded-md border border-zinc-700 bg-zinc-800 px-3 text-sm text-white"
                required
              >
                <option value="">Selecciona un equipo</option>
                {equipment?.map((eq) => (
                  <option key={eq.id} value={eq.id}>
                    {eq.brand} {eq.model} — {eq.serial_number}
                  </option>
                ))}
              </select>
            </div>

            <div className="space-y-2">
              <Label>Tipo de reparación</Label>
              <select
                value={tipo}
                onChange={(e) => setTipo(e.target.value)}
                className="w-full h-10 rounded-md border border-zinc-700 bg-zinc-800 px-3 text-sm text-white"
              >
                <option value="correctiva">Correctiva</option>
                <option value="preventiva">Preventiva</option>
                <option value="emergencia">Emergencia</option>
              </select>
            </div>

            <div className="space-y-2">
              <Label>Falla asociada (opcional)</Label>
              <select
                value={fallaId}
                onChange={(e) => setFallaId(e.target.value)}
                className="w-full h-10 rounded-md border border-zinc-700 bg-zinc-800 px-3 text-sm text-white"
              >
                <option value="">Sin falla (reparación directa)</option>
                {fallas?.map((f) => (
                  <option key={f.id} value={f.id}>
                    {f.parte} — {f.pieza} ({f.status})
                  </option>
                ))}
              </select>
            </div>

            <div className="space-y-2">
              <Label>Descripción del trabajo *</Label>
              <Textarea
                value={descripcion}
                onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setDescripcion(e.target.value)}
                placeholder="Describe qué se hizo: cambio de banda, reparación de fuga, servicio preventivo..."
                rows={3}
                required
              />
            </div>

            <div className="space-y-2">
              <Label>Notas (opcional)</Label>
              <Textarea
                value={notas}
                onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setNotas(e.target.value)}
                placeholder="Observaciones adicionales..."
                rows={2}
              />
            </div>

            <div className="flex gap-3 pt-4">
              <Button type="submit" disabled={!equipmentId || !descripcion.trim() || createMutation.isPending}>
                {createMutation.isPending ? (
                  <><Loader2 className="h-4 w-4 mr-2 animate-spin" /> Creando...</>
                ) : (
                  'Crear reparación'
                )}
              </Button>
              <Button type="button" variant="outline" onClick={() => navigate('/reparaciones')}>
                Cancelar
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
