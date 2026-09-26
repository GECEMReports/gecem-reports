import { useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router';
import { useQuery, useMutation } from '@tanstack/react-query';
import { listEquipment } from '@/api/equipment';
import { diagnose } from '@/api/diagnosis';
import type { DiagnosisResponse } from '@/schemas/diagnosis';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Stethoscope, MessageCircleQuestion } from 'lucide-react';

export default function DiagnosisPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const preselectedEquipment = searchParams.get('equipment') || '';

  const [equipmentId, setEquipmentId] = useState(preselectedEquipment);
  const [symptoms, setSymptoms] = useState('');
  const [followUpResponse, setFollowUpResponse] = useState('');
  const [followUpQuestion, setFollowUpQuestion] = useState<string | null>(null);
  const [threadId, setThreadId] = useState<string | null>(null);

  const { data: equipment } = useQuery({
    queryKey: ['equipment', 'list'],
    queryFn: listEquipment,
  });

  const mutation = useMutation({
    mutationFn: diagnose,
    onSuccess: (data: DiagnosisResponse) => {
      if (data.interrupted) {
        setThreadId(data.thread_id || null);
        setFollowUpQuestion(data.pregunta || 'Necesito más detalles.');
      } else {
        navigate('/diagnosis/result', { state: { diagnosis: data, equipment_id: equipmentId } });
      }
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setFollowUpQuestion(null);
    setFollowUpResponse('');
    setThreadId(null);
    mutation.mutate({ equipment_id: equipmentId, symptoms });
  };

  const handleFollowUpSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setFollowUpQuestion(null);
    setFollowUpResponse('');
    mutation.mutate({
      equipment_id: equipmentId,
      thread_id: threadId || undefined,
      respuesta_seguimiento: followUpResponse,
    });
  };

  return (
    <div className="max-w-2xl">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-white flex items-center gap-3">
          <Stethoscope className="h-8 w-8 text-yellow-500" />
          Diagnostico IA
        </h1>
        <p className="text-zinc-400 mt-1">Describe los sintomas y la IA analizara el problema</p>
      </div>

      <Card className="border-zinc-800 bg-zinc-900">
        <CardHeader>
          <CardTitle className="text-white">Nuevo diagnostico</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            {mutation.isError && (
              <div className="text-red-400 text-sm bg-red-950/50 p-2 rounded">
                Error al generar diagnostico. Intenta de nuevo.
              </div>
            )}
            <div className="space-y-2">
              <Label htmlFor="equipment">Equipo</Label>
              <select
                id="equipment"
                value={equipmentId}
                onChange={(e) => setEquipmentId(e.target.value)}
                className="w-full h-10 rounded-md border border-zinc-700 bg-zinc-800 px-3 text-sm text-white"
                required
              >
                <option value="">Selecciona un equipo</option>
                {equipment?.map((eq) => (
                  <option key={eq.id} value={eq.id}>
                    {eq.brand} {eq.model} — {eq.serial_number} ({eq.hours.toLocaleString()} hrs)
                  </option>
                ))}
              </select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="symptoms">Sintomas observados</Label>
              <Textarea
                id="symptoms"
                value={symptoms}
                onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setSymptoms(e.target.value)}
                placeholder="Describe los sintomas: ruidos, perdida de potencia, fugas, humo, vibraciones, etc."
                rows={5}
                required
                disabled={!!followUpQuestion}
              />
            </div>
            {!followUpQuestion && (
              <Button type="submit" disabled={mutation.isPending} className="w-full">
                {mutation.isPending ? 'Analizando con IA...' : 'Generar diagnostico'}
              </Button>
            )}
          </form>

          {followUpQuestion && (
            <div className="mt-6 space-y-4">
              <div className="rounded-lg border border-blue-500/30 bg-blue-500/10 p-4">
                <div className="flex items-start gap-3">
                  <MessageCircleQuestion className="h-5 w-5 text-blue-400 flex-shrink-0 mt-0.5" />
                  <div>
                    <p className="text-sm font-medium text-blue-400 mb-1">La IA necesita mas informacion</p>
                    <p className="text-sm text-zinc-300 whitespace-pre-wrap">{followUpQuestion}</p>
                  </div>
                </div>
              </div>

              <form onSubmit={handleFollowUpSubmit} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="followup">Tu respuesta</Label>
                  <Textarea
                    id="followup"
                    value={followUpResponse}
                    onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setFollowUpResponse(e.target.value)}
                    placeholder="Agrega los detalles que la IA te pide arriba..."
                    rows={4}
                    required
                  />
                </div>
                <div className="flex gap-3">
                  <Button type="submit" disabled={mutation.isPending || !followUpResponse.trim()} className="flex-1">
                    {mutation.isPending ? 'Analizando...' : 'Continuar diagnostico'}
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => {
                      setFollowUpQuestion(null);
                      setFollowUpResponse('');
                      setThreadId(null);
                    }}
                  >
                    Cancelar
                  </Button>
                </div>
              </form>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
