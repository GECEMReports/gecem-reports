import { useState } from 'react';
import { useNavigate } from 'react-router';
import { useMutation } from '@tanstack/react-query';
import { createEquipment } from '@/api/equipment';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

export default function EquipmentCreatePage() {
  const navigate = useNavigate();
  const [form, setForm] = useState({
    brand: '',
    model: '',
    serial_number: '',
    equipment_type: 'excavator',
    hours: 0,
    year: new Date().getFullYear(),
    notes: '',
  });

  const mutation = useMutation({
    mutationFn: createEquipment,
    onSuccess: () => navigate('/equipment'),
  });

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setForm((prev) => ({
      ...prev,
      [name]: name === 'hours' ? (value === '' ? '' : value) : name === 'year' ? (value === '' ? '' : parseInt(value, 10)) : value,
    }));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    mutation.mutate({
      ...form,
      hours: parseFloat(String(form.hours)) || 0,
      year: parseInt(String(form.year), 10) || undefined,
    });
  };

  return (
    <div className="max-w-2xl">
      <h1 className="text-3xl font-bold text-white mb-2">Nuevo equipo</h1>
      <p className="text-zinc-400 mb-6">Registra una maquina en tu inventario</p>

      <Card className="border-zinc-800 bg-zinc-900">
        <CardHeader>
          <CardTitle className="text-white">Datos del equipo</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            {mutation.isError && (
              <div className="text-red-400 text-sm bg-red-950/50 p-2 rounded">
                {(mutation.error as any)?.response?.data?.detail || 'Error al crear equipo'}
              </div>
            )}
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="brand">Marca</Label>
                <Input id="brand" name="brand" value={form.brand} onChange={handleChange} placeholder="CAT" required />
              </div>
              <div className="space-y-2">
                <Label htmlFor="model">Modelo</Label>
                <Input id="model" name="model" value={form.model} onChange={handleChange} placeholder="320" required />
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="serial_number">Numero de serie</Label>
              <Input id="serial_number" name="serial_number" value={form.serial_number} onChange={handleChange} placeholder="CAT0320XLHD01234" required />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="equipment_type">Tipo</Label>
                <select
                  id="equipment_type"
                  name="equipment_type"
                  value={form.equipment_type}
                  onChange={handleChange}
                  className="w-full h-10 rounded-md border border-zinc-700 bg-zinc-800 px-3 text-sm text-white"
                >
                  <option value="excavator">Excavadora</option>
                  <option value="loader">Cargador</option>
                  <option value="bulldozer">Bulldozer</option>
                  <option value="crane">Grua</option>
                  <option value="dump_truck">Volqueta</option>
                  <option value="backhoe">Retroexcavadora</option>
                  <option value="other">Otro</option>
                </select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="hours">Horas de operacion</Label>
                <Input id="hours" name="hours" type="number" step="any" value={form.hours} onChange={handleChange} placeholder="16628.2" />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="year">Ano</Label>
                <Input id="year" name="year" type="number" value={form.year} onChange={handleChange} />
              </div>
              <div className="space-y-2">
                <Label htmlFor="notes">Notas</Label>
                <Input id="notes" name="notes" value={form.notes} onChange={handleChange} placeholder="Opcional" />
              </div>
            </div>
            <div className="flex gap-4 pt-4">
              <Button type="submit" disabled={mutation.isPending}>
                {mutation.isPending ? 'Creando...' : 'Crear equipo'}
              </Button>
              <Button type="button" variant="outline" onClick={() => navigate('/equipment')}>
                Cancelar
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
