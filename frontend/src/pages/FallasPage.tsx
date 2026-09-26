import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router';
import { listFallas } from '@/api/falla';
import { listEquipment } from '@/api/equipment';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { AlertTriangle, Plus, Search, Filter } from 'lucide-react';

const prioridadConfig: Record<string, { label: string; color: string }> = {
  baja: { label: 'Baja', color: 'bg-green-500/20 text-green-400 border-green-500/30' },
  normal: { label: 'Normal', color: 'bg-blue-500/20 text-blue-400 border-blue-500/30' },
  urgente: { label: 'Urgente', color: 'bg-orange-500/20 text-orange-400 border-orange-500/30' },
  critica: { label: 'Crítica', color: 'bg-red-500/20 text-red-400 border-red-500/30' },
};

const statusConfig: Record<string, { label: string; color: string }> = {
  detectada: { label: 'Detectada', color: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30' },
  en_reparacion: { label: 'En reparación', color: 'bg-blue-500/20 text-blue-400 border-blue-500/30' },
  terminada: { label: 'Terminada', color: 'bg-green-500/20 text-green-400 border-green-500/30' },
};

export default function FallasPage() {
  const [filterEquipment, setFilterEquipment] = useState('');
  const [filterStatus, setFilterStatus] = useState('');
  const [filterPrioridad, setFilterPrioridad] = useState('');
  const [searchText, setSearchText] = useState('');

  const { data: fallas, isLoading: loadingFallas } = useQuery({
    queryKey: ['fallas', filterEquipment],
    queryFn: () => listFallas(filterEquipment || undefined),
  });

  const { data: equipment } = useQuery({
    queryKey: ['equipment', 'list'],
    queryFn: listEquipment,
  });

  const filteredFallas = fallas?.filter((f) => {
    if (filterStatus && f.status !== filterStatus) return false;
    if (filterPrioridad && f.prioridad !== filterPrioridad) return false;
    if (searchText) {
      const q = searchText.toLowerCase();
      const match =
        f.parte.toLowerCase().includes(q) ||
        f.pieza.toLowerCase().includes(q) ||
        f.descripcion.toLowerCase().includes(q) ||
        (f.causa_raiz || '').toLowerCase().includes(q);
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
          <h1 className="text-3xl font-bold text-white">Fallas</h1>
          <p className="text-zinc-400">Historial de fallas detectadas</p>
        </div>
        <Link to="/diagnosis">
          <Button>
            <Plus className="h-4 w-4 mr-2" />
            Nuevo diagnostico
          </Button>
        </Link>
      </div>

      {/* Filters */}
      <Card className="border-zinc-800 bg-zinc-900">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm text-zinc-400 flex items-center gap-2">
            <Filter className="h-4 w-4" />
            Filtros
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-zinc-500" />
              <Input
                placeholder="Buscar parte, pieza..."
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
            <select
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
              className="h-9 rounded-md border border-zinc-700 bg-zinc-800 px-3 text-sm text-white"
            >
              <option value="">Todos los estados</option>
              <option value="detectada">Detectada</option>
              <option value="en_reparacion">En reparación</option>
              <option value="terminada">Terminada</option>
            </select>
            <select
              value={filterPrioridad}
              onChange={(e) => setFilterPrioridad(e.target.value)}
              className="h-9 rounded-md border border-zinc-700 bg-zinc-800 px-3 text-sm text-white"
            >
              <option value="">Todas las prioridades</option>
              <option value="baja">Baja</option>
              <option value="normal">Normal</option>
              <option value="urgente">Urgente</option>
              <option value="critica">Crítica</option>
            </select>
          </div>
        </CardContent>
      </Card>

      {/* List */}
      {loadingFallas ? (
        <div className="text-zinc-400">Cargando fallas...</div>
      ) : filteredFallas?.length === 0 ? (
        <Card className="border-zinc-800 bg-zinc-900">
          <CardContent className="flex flex-col items-center justify-center py-12">
            <AlertTriangle className="h-12 w-12 text-zinc-600 mb-4" />
            <p className="text-zinc-400 mb-4">No hay fallas registradas</p>
            <Link to="/diagnosis">
              <Button variant="outline">Crear primer diagnostico</Button>
            </Link>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {filteredFallas?.map((falla) => {
            const prioridad = prioridadConfig[falla.prioridad] || prioridadConfig.normal;
            const status = statusConfig[falla.status] || statusConfig.detectada;
            return (
              <Link key={falla.id} to={`/fallas/${falla.id}`}>
                <Card className="border-zinc-800 bg-zinc-900 hover:border-zinc-700 transition-colors cursor-pointer">
                  <CardContent className="py-4">
                    <div className="flex items-center justify-between">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-3 mb-1">
                          <h3 className="text-white font-medium truncate">
                            {falla.parte} — {falla.pieza}
                          </h3>
                          <Badge variant="outline" className={prioridad.color}>
                            {prioridad.label}
                          </Badge>
                          <Badge variant="outline" className={status.color}>
                            {status.label}
                          </Badge>
                        </div>
                        <p className="text-sm text-zinc-400 truncate">
                          {falla.descripcion}
                        </p>
                        <div className="flex items-center gap-4 mt-2 text-xs text-zinc-500">
                          <span>{getEquipmentName(falla.equipment_id)}</span>
                          <span>{new Date(falla.created_at).toLocaleDateString('es-MX')}</span>
                          {falla.fotos.length > 0 && (
                            <span>{falla.fotos.length} foto(s)</span>
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
