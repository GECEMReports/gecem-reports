import { useQuery } from '@tanstack/react-query';
import { listEquipment } from '@/api/equipment';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Truck, Stethoscope, Wrench } from 'lucide-react';
import { Link } from 'react-router';
import { Button } from '@/components/ui/button';

export default function DashboardPage() {
  const { data: equipment } = useQuery({
    queryKey: ['equipment'],
    queryFn: listEquipment,
  });

  const stats = [
    {
      label: 'Equipos registrados',
      value: equipment?.length ?? 0,
      icon: Truck,
      color: 'text-blue-400',
      bg: 'bg-blue-500/10',
    },
    {
      label: 'Total horas operadas',
      value: equipment?.reduce((sum, e) => sum + e.hours, 0).toLocaleString() ?? '0',
      icon: Wrench,
      color: 'text-yellow-400',
      bg: 'bg-yellow-500/10',
    },
    {
      label: 'Marcas diferentes',
      value: new Set(equipment?.map((e) => e.brand)).size ?? 0,
      icon: Stethoscope,
      color: 'text-green-400',
      bg: 'bg-green-500/10',
    },
  ];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-white">Dashboard</h1>
        <p className="text-zinc-400">Resumen de tu taller</p>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        {stats.map(({ label, value, icon: Icon, color, bg }) => (
          <Card key={label} className="border-zinc-800 bg-zinc-900">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-zinc-400">{label}</CardTitle>
              <div className={`p-2 rounded-lg ${bg}`}>
                <Icon className={`h-5 w-5 ${color}`} />
              </div>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-white">{value}</div>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card className="border-zinc-800 bg-zinc-900">
          <CardHeader>
            <CardTitle className="text-white">Acciones rapidas</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <Link to="/equipment/new">
              <Button variant="outline" className="w-full justify-start">
                <Truck className="h-4 w-4 mr-2" />
                Registrar nuevo equipo
              </Button>
            </Link>
            <Link to="/diagnosis">
              <Button variant="outline" className="w-full justify-start">
                <Stethoscope className="h-4 w-4 mr-2" />
                Iniciar diagnostico IA
              </Button>
            </Link>
          </CardContent>
        </Card>

        <Card className="border-zinc-800 bg-zinc-900">
          <CardHeader>
            <CardTitle className="text-white">Equipos recientes</CardTitle>
          </CardHeader>
          <CardContent>
            {equipment?.length === 0 ? (
              <p className="text-zinc-400 text-sm">No hay equipos registrados</p>
            ) : (
              <div className="space-y-2">
                {equipment?.slice(0, 5).map((eq) => (
                  <div key={eq.id} className="flex items-center justify-between text-sm">
                    <span className="text-zinc-300">{eq.brand} {eq.model}</span>
                    <span className="text-zinc-500">{eq.hours.toLocaleString()} hrs</span>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
