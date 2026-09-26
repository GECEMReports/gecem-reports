import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router';
import { listReparaciones } from '@/api/falla';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Clock, Plus, Search, Wrench } from 'lucide-react';

const tipoConfig: Record<string, { label: string; color: string }> = {
  preventiva: { label: 'Preventiva', color: 'bg-green-500/20 text-green-400 border-green-500/30' },
  correctiva: { label: 'Correctiva', color: 'bg-blue-500/20 text-blue-400 border-blue-500/30' },
  emergencia: { label: 'Emergencia', color: 'bg-red-500/20 text-red-400 border-red-500/30' },
};

const statusConfig: Record<string, { label: string; color: string }> = {
  en_progreso: { label: 'En progreso', color: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30' },
  completado: { label: 'Completada', color: 'bg-green-500/20 text-green-400 border-green-500/30' },
};

export default function ReparacionesPage() {
  const [filterEquipment, setFilterEquipment] = useState('');
  const [searchText, setSearchText] = useState('');

  const { data: reparaciones, isLoading } = useQuery({
    queryKey: ['reparaciones', filterEquipment],
    queryFn: () => listReparaciones(filterEquipment || undefined),
  });

  const { data: equipment } = useQuery({
    queryKey: ['equipment', 'list'],
    queryFn: () => import('@/api/equipment').then(m => m.listEquipment()),
  });

  const filtered = reparaciones?.filter((r) => {
    if (searchText) {
      const q = searchText.toLowerCase();
      const match =
        r.descripcion.toLowerCase().includes(q) ||
        r.notas?.toLowerCase().includes(q);
      if (!match) return false;
    }
    return true;
  });

  const getEquipmentName = (id: string) => {
    const eq = equipment?.find((e) => e.id === id);
    return eq ? `${eq.brand} ${eq.model}` : id.slice(0, 8);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white">Reparaciones</h1>
          <p className="text-zinc-400">Registro de trabajos realizados</p>
        </div>
        <Link to="/reparaciones/new">
          <Button>
            <Plus className="h-4 w-4 mr-2" />
            Nueva reparación
          </Button>
        </Link>
      </div>

      {/* Filters */}
      <Card className="border-zinc-800 bg-zinc-900">
        <CardContent className="py-3">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-zinc-500" />
              <Input
                placeholder="Buscar descripcion..."
                value={searchText}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setSearchText(e.target.value)}
                className="pl-9"
              />
            </div>
            <select
              value={filterEquipment}
              onChange={(e) => setFilterEquipment(e.target.value)}
              className="h-9 rounded-md border border-zinc-700 bg-zinc-800 px-3 text-sm text-white"
            >
              <option value="">Todos los equipos</option>
              {equipment?.map((eq) => (
                <option key={eq.id} value={eq.id}>
                  {eq.brand} {eq.model}
                </option>
              ))}
            </select>
          </div>
        </CardContent>
      </Card>

      {/* List */}
      {isLoading ? (
        <div className="text-zinc-400">Cargando reparaciones...</div>
      ) : filtered?.length === 0 ? (
        <Card className="border-zinc-800 bg-zinc-900">
          <CardContent className="flex flex-col items-center justify-center py-12">
            <Wrench className="h-12 w-12 text-zinc-600 mb-4" />
            <p className="text-zinc-400 mb-4">No hay reparaciones registradas</p>
            <Link to="/reparaciones/new">
              <Button variant="outline">Crear primera reparación</Button>
            </Link>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {filtered?.map((rep) => {
            const tipo = tipoConfig[rep.tipo] || tipoConfig.correctiva;
            const status = statusConfig[rep.status] || statusConfig.en_progreso;
            return (
              <Link key={rep.id} to={`/reparaciones/${rep.id}`}>
                <Card className="border-zinc-800 bg-zinc-900 hover:border-zinc-700 transition-colors cursor-pointer">
                  <CardContent className="py-4">
                    <div className="flex items-center justify-between">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-3 mb-1">
                          <h3 className="text-white font-medium truncate">
                            {rep.descripcion || 'Sin descripcion'}
                          </h3>
                          <Badge variant="outline" className={tipo.color}>
                            {tipo.label}
                          </Badge>
                          <Badge variant="outline" className={status.color}>
                            {status.label}
                          </Badge>
                        </div>
                        <div className="flex items-center gap-4 text-xs text-zinc-500">
                          <span>{getEquipmentName(rep.equipment_id)}</span>
                          <span className="flex items-center gap-1">
                            <Clock className="h-3 w-3" />
                            {rep.tiempo_total_horas > 0
                              ? `${rep.tiempo_total_horas} hrs`
                              : 'En progreso'}
                          </span>
                          <span>{rep.pasos.length} pasos</span>
                          <span>{new Date(rep.created_at).toLocaleDateString('es-MX')}</span>
                          {rep.falla_id && (
                            <Badge variant="outline" className="bg-zinc-800 text-zinc-500 border-zinc-700 text-[10px]">
                              Desde falla
                            </Badge>
                          )}
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}
