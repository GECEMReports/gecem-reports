import { useState } from 'react';
import { useNavigate, useSearchParams, useLocation } from 'react-router';
import { useQuery, useMutation } from '@tanstack/react-query';
import { listEquipment } from '@/api/equipment';
import { estructurarFalla, createFalla, uploadFallaFoto } from '@/api/falla';
import type { FallaEstructurada } from '@/schemas/falla';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { AlertTriangle, Camera, Check, Loader2, MessageCircleQuestion, Upload } from 'lucide-react';

const prioridadConfig: Record<string, { label: string; color: string }> = {
  baja: { label: 'Baja', color: 'bg-green-500/20 text-green-400 border-green-500/30' },
  normal: { label: 'Normal', color: 'bg-blue-500/20 text-blue-400 border-blue-500/30' },
  urgente: { label: 'Urgente', color: 'bg-orange-500/20 text-orange-400 border-orange-500/30' },
  critica: { label: 'Crítica', color: 'bg-red-500/20 text-red-400 border-red-500/30' },
};

type Step = 'form' | 'structuring' | 'review' | 'photos' | 'done';

export default function FallaPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const location = useLocation();
  const locationState = location.state as { diagnosis_text?: string; equipment_id?: string } | null;

  const preselectedEquipment = searchParams.get('equipment') || locationState?.equipment_id || '';
  const diagnosisId = searchParams.get('diagnosis') || '';
  const diagnosisText = locationState?.diagnosis_text || '';

  const [step, setStep] = useState<Step>('form');
  const [equipmentId, setEquipmentId] = useState(preselectedEquipment);
  const [descripcionMecanico, setDescripcionMecanico] = useState('');
  const [followUpQuestion, setFollowUpQuestion] = useState<string | null>(null);
  const [followUpResponse, setFollowUpResponse] = useState('');
  const [originalDescripcion, setOriginalDescripcion] = useState('');

  const [fallaEstructurada, setFallaEstructurada] = useState<FallaEstructurada | null>(null);
  const [createdFallaId, setCreatedFallaId] = useState<string | null>(null);
  const [uploadedPhotos, setUploadedPhotos] = useState<File[]>([]);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const { data: equipment } = useQuery({
    queryKey: ['equipment', 'list'],
    queryFn: listEquipment,
  });

  const estructurarMutation = useMutation({
    mutationFn: () =>
      estructurarFalla(equipmentId, diagnosisText, descripcionMecanico),
    onSuccess: (data) => {
      setErrorMessage(null);
      if (data.necesita_mas_info) {
        setFollowUpQuestion(data.pregunta_seguimiento || 'Necesito más detalles.');
        if (!originalDescripcion) {
          setOriginalDescripcion(descripcionMecanico);
        }
      } else {
        setFallaEstructurada(data.falla_estructurada || null);
        setStep('review');
      }
    },
    onError: (error: any) => {
      const msg = error?.response?.data?.detail || error?.message || 'Error al conectar con la IA';
      setErrorMessage(msg);
      setStep('form');
    },
  });

  const createFallaMutation = useMutation({
    mutationFn: async () => {
      if (!fallaEstructurada) throw new Error('No falla estructurada');
      const falla = await createFalla({
        equipment_id: equipmentId,
        diagnosis_id: diagnosisId || undefined,
        parte: fallaEstructurada.parte,
        pieza: fallaEstructurada.pieza,
        descripcion: fallaEstructurada.descripcion,
        causa_raiz: fallaEstructurada.causa_raiz,
        prioridad: fallaEstructurada.prioridad,
      });
      return falla;
    },
    onSuccess: (falla) => {
      setCreatedFallaId(falla.id);
      setStep('photos');
    },
  });

  const uploadPhotosMutation = useMutation({
    mutationFn: async () => {
      if (!createdFallaId) return;
      for (const file of uploadedPhotos) {
        await uploadFallaFoto(createdFallaId, file);
      }
    },
    onSuccess: () => {
      setStep('done');
    },
  });

  const handleEstructurar = (e: React.FormEvent) => {
    e.preventDefault();
    if (!descripcionMecanico.trim()) return;
    setErrorMessage(null);
    setFollowUpQuestion(null);
    setFollowUpResponse('');
    setStep('structuring');
    estructurarMutation.mutate();
  };

  const handleFollowUpSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const base = originalDescripcion || descripcionMecanico;
    const expanded = `${base}\n\nInformación adicional: ${followUpResponse}`;
    setDescripcionMecanico(expanded);
    setFollowUpQuestion(null);
    setFollowUpResponse('');
    estructurarMutation.mutate();
  };

  const handlePhotoSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setUploadedPhotos(Array.from(e.target.files));
    }
  };

  return (
    <div className="max-w-2xl space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-white flex items-center gap-3">
          <AlertTriangle className="h-8 w-8 text-yellow-500" />
          Registrar Falla Real
        </h1>
        <p className="text-zinc-400 mt-1">
          Documenta la falla encontrada durante la reparación
        </p>
      </div>

      {/* Step 1: Form */}
      {step === 'form' && (
        <Card className="border-zinc-800 bg-zinc-900">
          <CardHeader>
            <CardTitle className="text-white">Descripción de la falla</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleEstructurar} className="space-y-4">
              {errorMessage && (
                <div className="text-red-400 text-sm bg-red-950/50 p-3 rounded border border-red-500/30">
                  {errorMessage}
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
                      {eq.brand} {eq.model} — {eq.serial_number}
                    </option>
                  ))}
                </select>
              </div>

              {diagnosisText && (
                <div className="rounded-lg border border-zinc-700 bg-zinc-800/50 p-3">
                  <p className="text-xs text-zinc-500 mb-1">Diagnóstico IA previo:</p>
                  <p className="text-sm text-zinc-300 line-clamp-3">{diagnosisText}</p>
                </div>
              )}

              <div className="space-y-2">
                <Label htmlFor="descripcion">¿Qué encontraste realmente?</Label>
                <Textarea
                  id="descripcion"
                  value={descripcionMecanico}
                  onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) =>
                    setDescripcionMecanico(e.target.value)
                  }
                  placeholder="Describe la falla real que encontraste: qué parte está dañada, qué pieza específica, cómo se ve el daño, qué causó el problema..."
                  rows={6}
                  required
                  disabled={!!followUpQuestion}
                />
              </div>

              {!followUpQuestion && (
                <Button
                  type="submit"
                  disabled={estructurarMutation.isPending}
                  className="w-full"
                >
                  {estructurarMutation.isPending ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Analizando con IA...
                    </>
                  ) : (
                    'Estructurar falla con IA'
                  )}
                </Button>
              )}
            </form>

            {/* Follow-up question */}
            {followUpQuestion && (
              <div className="mt-6 space-y-4">
                <div className="rounded-lg border border-blue-500/30 bg-blue-500/10 p-4">
                  <div className="flex items-start gap-3">
                    <MessageCircleQuestion className="h-5 w-5 text-blue-400 flex-shrink-0 mt-0.5" />
                    <div>
                      <p className="text-sm font-medium text-blue-400 mb-1">
                        La IA necesita más información
                      </p>
                      <p className="text-sm text-zinc-300 whitespace-pre-wrap">
                        {followUpQuestion}
                      </p>
                    </div>
                  </div>
                </div>

                <form onSubmit={handleFollowUpSubmit} className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="followup">Tu respuesta</Label>
                    <Textarea
                      id="followup"
                      value={followUpResponse}
                      onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) =>
                        setFollowUpResponse(e.target.value)
                      }
                      placeholder="Agrega los detalles que la IA te pide arriba..."
                      rows={4}
                      required
                    />
                  </div>
                  <div className="flex gap-3">
                    <Button
                      type="submit"
                      disabled={estructurarMutation.isPending || !followUpResponse.trim()}
                      className="flex-1"
                    >
                      {estructurarMutation.isPending ? 'Analizando...' : 'Continuar'}
                    </Button>
                    <Button
                      type="button"
                      variant="outline"
                      onClick={() => {
                        setFollowUpQuestion(null);
                        setFollowUpResponse('');
                        setOriginalDescripcion('');
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
      )}

      {/* Step 2: Structuring */}
      {step === 'structuring' && (
        <Card className="border-zinc-800 bg-zinc-900">
          <CardContent className="flex flex-col items-center justify-center py-12">
            <Loader2 className="h-12 w-12 text-yellow-500 animate-spin mb-4" />
            <p className="text-zinc-300 text-lg">Analizando falla con IA...</p>
            <p className="text-zinc-500 text-sm mt-1">Esto puede tomar hasta 2 minutos</p>
            <Button
              variant="outline"
              className="mt-6"
              onClick={() => {
                setStep('form');
                estructurarMutation.reset();
              }}
            >
              Cancelar
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Step 3: Review */}
      {step === 'review' && fallaEstructurada && (
        <Card className="border-zinc-800 bg-zinc-900">
          <CardHeader>
            <CardTitle className="text-white">Falla estructurada</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-xs text-zinc-500">Parte</p>
                <p className="text-white font-medium">{fallaEstructurada.parte}</p>
              </div>
              <div>
                <p className="text-xs text-zinc-500">Pieza</p>
                <p className="text-white font-medium">{fallaEstructurada.pieza}</p>
              </div>
            </div>

            <div>
              <p className="text-xs text-zinc-500">Descripción</p>
              <p className="text-zinc-300 text-sm">{fallaEstructurada.descripcion}</p>
            </div>

            <div>
              <p className="text-xs text-zinc-500">Causa raíz</p>
              <p className="text-zinc-300 text-sm">{fallaEstructurada.causa_raiz}</p>
            </div>

            <div className="flex gap-3">
              <Badge
                variant="outline"
                className={prioridadConfig[fallaEstructurada.prioridad]?.color || 'bg-zinc-800'}
              >
                Prioridad: {prioridadConfig[fallaEstructurada.prioridad]?.label || fallaEstructurada.prioridad}
              </Badge>
              <Badge variant="outline" className="bg-zinc-800 text-zinc-300 border-zinc-700">
                Severidad: {fallaEstructurada.severidad}
              </Badge>
            </div>

            <div className="flex gap-3 pt-4">
              <Button
                onClick={() => createFallaMutation.mutate()}
                disabled={createFallaMutation.isPending}
                className="flex-1"
              >
                {createFallaMutation.isPending ? 'Guardando...' : 'Confirmar y guardar'}
              </Button>
              <Button variant="outline" onClick={() => setStep('form')}>
                Editar
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Step 4: Photos */}
      {step === 'photos' && (
        <Card className="border-zinc-800 bg-zinc-900">
          <CardHeader>
            <CardTitle className="text-white flex items-center gap-2">
              <Camera className="h-5 w-5 text-yellow-500" />
              Evidencia fotográfica
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-zinc-400 text-sm">
              Sube fotos de la falla para documentar el daño (opcional)
            </p>

            <div className="space-y-2">
              <Label htmlFor="fotos">Seleccionar fotos</Label>
              <Input
                id="fotos"
                type="file"
                accept="image/*"
                multiple
                capture="environment"
                onChange={handlePhotoSelect}
                className="cursor-pointer"
              />
            </div>

            {uploadedPhotos.length > 0 && (
              <div className="grid grid-cols-3 gap-2">
                {uploadedPhotos.map((file, i) => (
                  <div
                    key={i}
                    className="aspect-square rounded-lg bg-zinc-800 flex items-center justify-center overflow-hidden"
                  >
                    <img
                      src={URL.createObjectURL(file)}
                      alt={`Foto ${i + 1}`}
                      className="w-full h-full object-cover"
                    />
                  </div>
                ))}
              </div>
            )}

            <div className="flex gap-3">
              <Button
                onClick={() => uploadPhotosMutation.mutate()}
                disabled={uploadPhotosMutation.isPending}
                className="flex-1"
              >
                {uploadPhotosMutation.isPending ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Subiendo...
                  </>
                ) : (
                  <>
                    <Upload className="h-4 w-4 mr-2" />
                    Subir fotos
                  </>
                )}
              </Button>
              <Button variant="outline" onClick={() => setStep('done')}>
                Omitir
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Step 5: Done */}
      {step === 'done' && (
        <Card className="border-zinc-800 bg-zinc-900">
          <CardContent className="flex flex-col items-center justify-center py-12">
            <div className="w-16 h-16 rounded-full bg-green-500/20 flex items-center justify-center mb-4">
              <Check className="h-8 w-8 text-green-400" />
            </div>
            <p className="text-white text-lg font-medium">Falla registrada</p>
            <p className="text-zinc-400 text-sm mt-1">
              La falla ha sido documentada correctamente
            </p>
            <div className="flex gap-3 mt-6">
              <Button onClick={() => navigate('/equipment')}>
                Ver equipos
              </Button>
              <Button variant="outline" onClick={() => navigate('/diagnosis')}>
                Nuevo diagnóstico
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
