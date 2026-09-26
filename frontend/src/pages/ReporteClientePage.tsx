import { useState } from 'react';
import { useParams, Link } from 'react-router';
import { useQuery, useMutation } from '@tanstack/react-query';
import { getFalla, generarReporte, downloadReportePdf } from '@/api/falla';
import type { ReporteCliente } from '@/schemas/falla';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  ArrowLeft,
  Download,
  FileText,
  Loader2,
  Sparkles,
} from 'lucide-react';

export default function ReporteClientePage() {
  const { id: fallaId } = useParams<{ id: string }>();
  const [reporte, setReporte] = useState<ReporteCliente | null>(null);
  const [pdfPending, setPdfPending] = useState(false);
  const [pdfError, setPdfError] = useState<string | null>(null);

  const handleDownloadPdf = async () => {
    if (!reporte) return;
    setPdfError(null);
    setPdfPending(true);
    try {
      await downloadReportePdf(reporte.id);
    } catch (error) {
      setPdfError(error instanceof Error ? error.message : 'No se pudo descargar el PDF');
    } finally {
      setPdfPending(false);
    }
  };

  const { data: falla } = useQuery({
    queryKey: ['falla', fallaId],
    queryFn: () => getFalla(fallaId!),
    enabled: !!fallaId,
  });

  const generarMutation = useMutation({
    mutationFn: () => generarReporte(fallaId!),
    onSuccess: (data) => {
      setReporte(data);
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
            <FileText className="h-6 w-6 text-yellow-500" />
            Reporte para Cliente
          </h1>
          {falla && (
            <p className="text-zinc-400 text-sm">{falla.parte} — {falla.pieza}</p>
          )}
        </div>
      </div>

      {/* Generate */}
      {!reporte && (
        <Card className="border-zinc-800 bg-zinc-900">
          <CardContent className="py-8 text-center">
            <Sparkles className="h-12 w-12 text-yellow-500 mx-auto mb-4" />
            <p className="text-zinc-300 mb-2">Genera un reporte profesional para tu cliente</p>
            <p className="text-zinc-500 text-sm mb-4">
              La IA resumirá el diagnóstico, trabajo realizado, refacciones y recomendaciones
            </p>
            <Button
              onClick={() => generarMutation.mutate()}
              disabled={generarMutation.isPending}
            >
              {generarMutation.isPending ? (
                <><Loader2 className="h-4 w-4 mr-2 animate-spin" /> Generando reporte...</>
              ) : (
                <><Sparkles className="h-4 w-4 mr-2" /> Generar con IA</>
              )}
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Loading */}
      {generarMutation.isPending && (
        <Card className="border-zinc-800 bg-zinc-900">
          <CardContent className="flex flex-col items-center justify-center py-12">
            <Loader2 className="h-12 w-12 text-yellow-500 animate-spin mb-4" />
            <p className="text-zinc-300 text-lg">Generando reporte profesional...</p>
            <p className="text-zinc-500 text-sm mt-1">Esto puede tomar hasta 2 minutos</p>
          </CardContent>
        </Card>
      )}

      {/* Report generated */}
      {reporte && (
        <>
          <Card className="border-green-500/30 bg-green-950/20">
            <CardContent className="py-4 flex items-center gap-3">
              <FileText className="h-5 w-5 text-green-400" />
              <div>
                <p className="text-green-400 font-medium">Reporte generado</p>
                <p className="text-zinc-400 text-sm">
                  {new Date(reporte.fecha_generacion).toLocaleDateString('es-MX')}
                </p>
              </div>
            </CardContent>
          </Card>

          {/* Content preview */}
          <Card className="border-zinc-800 bg-zinc-900">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm text-zinc-400">Contenido del reporte</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-sm text-zinc-300 whitespace-pre-wrap leading-relaxed">
                {reporte.contenido}
              </div>
            </CardContent>
          </Card>

          {/* Actions */}
          <div className="flex gap-3">
            <Button onClick={handleDownloadPdf} disabled={pdfPending}>
              {pdfPending ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <Download className="h-4 w-4 mr-2" />
              )}
              Descargar PDF
            </Button>
            <Link to={`/fallas/${fallaId}`}>
              <Button variant="outline">Volver a falla</Button>
            </Link>
          </div>
          {pdfError && (
            <p className="text-sm text-red-400" role="alert">
              {pdfError}
            </p>
          )}
        </>
      )}
    </div>
  );
}
