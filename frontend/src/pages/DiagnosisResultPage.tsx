import { useLocation, Link } from 'react-router';
import type { DiagnosisResponse } from '@/schemas/diagnosis';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ArrowLeft, AlertTriangle, Clock, Wrench, Package } from 'lucide-react';

const severityConfig = {
  low: { label: 'Baja', color: 'bg-green-500/20 text-green-400 border-green-500/30' },
  medium: { label: 'Media', color: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30' },
  high: { label: 'Alta', color: 'bg-orange-500/20 text-orange-400 border-orange-500/30' },
  critical: { label: 'Critica', color: 'bg-red-500/20 text-red-400 border-red-500/30' },
};

export default function DiagnosisResultPage() {
  const location = useLocation();
  const diagnosis = location.state?.diagnosis as DiagnosisResponse | undefined;

  if (!diagnosis) {
    return (
      <div className="text-center py-12">
        <p className="text-zinc-400 mb-4">No hay resultado de diagnostico</p>
        <Link to="/diagnosis">
          <Button variant="outline">Ir a diagnostico</Button>
        </Link>
      </div>
    );
  }

  const severity = severityConfig[diagnosis.severity ?? 'medium'] || severityConfig.medium;

  return (
    <div className="max-w-3xl space-y-6">
      <div className="flex items-center gap-4">
        <Link to="/diagnosis">
          <Button variant="ghost" size="icon">
            <ArrowLeft className="h-5 w-5" />
          </Button>
        </Link>
        <div>
          <h1 className="text-3xl font-bold text-white">Resultado del diagnostico</h1>
          <p className="text-zinc-400">Analisis generado por IA</p>
        </div>
      </div>

      <div className="flex items-center gap-4">
        <Badge variant="outline" className={severity.color}>
          <AlertTriangle className="h-3 w-3 mr-1" />
          Severidad: {severity.label}
        </Badge>
        <Badge variant="outline" className="bg-zinc-800 text-zinc-300 border-zinc-700">
          Tipo: {diagnosis.problem_type}
        </Badge>
        <Badge variant="outline" className="bg-zinc-800 text-zinc-300 border-zinc-700">
          <Clock className="h-3 w-3 mr-1" />
          {diagnosis.estimated_hours} hrs estimadas
        </Badge>
      </div>

      <Card className="border-zinc-800 bg-zinc-900">
        <CardHeader>
          <CardTitle className="text-white flex items-center gap-2">
            <Wrench className="h-5 w-5 text-yellow-500" />
            Diagnostico
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-zinc-300 leading-relaxed whitespace-pre-wrap">{diagnosis.diagnosis}</p>
        </CardContent>
      </Card>

      <Card className="border-zinc-800 bg-zinc-900">
        <CardHeader>
          <CardTitle className="text-white">Recomendaciones</CardTitle>
        </CardHeader>
        <CardContent>
          <ol className="space-y-2">
            {(diagnosis.recommendations ?? []).map((rec, i) => (
              <li key={i} className="flex gap-3 text-zinc-300">
                <span className="flex-shrink-0 w-6 h-6 rounded-full bg-yellow-500/20 text-yellow-400 text-xs flex items-center justify-center font-bold">
                  {i + 1}
                </span>
                {rec}
              </li>
            ))}
          </ol>
        </CardContent>
      </Card>

      {(diagnosis.parts_needed ?? []).length > 0 && (
        <Card className="border-zinc-800 bg-zinc-900">
          <CardHeader>
            <CardTitle className="text-white flex items-center gap-2">
              <Package className="h-5 w-5 text-yellow-500" />
              Refacciones necesarias
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2">
              {(diagnosis.parts_needed ?? []).map((part, i) => (
                <li key={i} className="flex items-center gap-2 text-zinc-300">
                  <span className="w-2 h-2 rounded-full bg-yellow-500" />
                  {part}
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      <div className="flex gap-4">
        <Link to={`/falla?equipment=${location.state?.equipment_id || ''}`} state={{ diagnosis_text: diagnosis.diagnosis || '', equipment_id: location.state?.equipment_id || '' }}>
          <Button>Registrar falla real</Button>
        </Link>
        <Link to="/diagnosis">
          <Button variant="outline">Nuevo diagnostico</Button>
        </Link>
        <Link to="/equipment">
          <Button variant="ghost">Ver equipos</Button>
        </Link>
      </div>
    </div>
  );
}
