import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router';
import { listEquipment } from '@/api/equipment';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Plus, Truck } from 'lucide-react';

export default function EquipmentListPage() {
  const { data: equipment, isLoading } = useQuery({
    queryKey: ['equipment'],
    queryFn: listEquipment,
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white">Equipos</h1>
          <p className="text-zinc-400">Maquinaria registrada en tu taller</p>
        </div>
        <Link to="/equipment/new">
          <Button>
            <Plus className="h-4 w-4 mr-2" />
            Nuevo equipo
          </Button>
        </Link>
      </div>

      {isLoading ? (
        <div className="text-zinc-400">Cargando equipos...</div>
      ) : equipment?.length === 0 ? (
        <Card className="border-zinc-800 bg-zinc-900">
          <CardContent className="flex flex-col items-center justify-center py-12">
            <Truck className="h-12 w-12 text-zinc-600 mb-4" />
            <p className="text-zinc-400 mb-4">No hay equipos registrados</p>
            <Link to="/equipment/new">
              <Button variant="outline">Registrar primer equipo</Button>
            </Link>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {equipment?.map((eq) => (
            <Card key={eq.id} className="border-zinc-800 bg-zinc-900 hover:border-zinc-700 transition-colors">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle className="text-white text-lg">
                    {eq.brand} {eq.model}
                  </CardTitle>
                  <Badge variant="outline" className="text-xs">
                    {eq.equipment_type}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="space-y-2 text-sm text-zinc-400">
                <p>Serie: {eq.serial_number}</p>
                <p>Horas: {eq.hours.toLocaleString()}</p>
                {eq.year && <p>Ano: {eq.year}</p>}
                <div className="pt-2">
                  <Link to={`/diagnosis?equipment=${eq.id}`}>
                    <Button variant="outline" size="sm" className="w-full">
                      Diagnosticar
                    </Button>
                  </Link>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
