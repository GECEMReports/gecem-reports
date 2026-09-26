import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router';
import { listEquipment, updateEquipment } from '@/api/equipment';
import type { Equipment, EquipmentUpdate } from '@/schemas/equipment';
import api from '@/api/client';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Dialog } from '@/components/ui/dialog';
import { Plus, Trash2, Truck, Pencil } from 'lucide-react';

const EQUIPMENT_TYPES = [
  { value: 'excavator', label: 'Excavadora' },
  { value: 'loader', label: 'Cargador' },
  { value: 'bulldozer', label: 'Bulldozer' },
  { value: 'crane', label: 'Grua' },
  { value: 'dump_truck', label: 'Volqueta' },
  { value: 'backhoe', label: 'Retroexcavadora' },
  { value: 'other', label: 'Otro' },
];

export default function EquipmentListPage() {
  const queryClient = useQueryClient();
  const [deleteError, setDeleteError] = useState<string | null>(null);

  // Edit dialog state
  const [editOpen, setEditOpen] = useState(false);
  const [editEquipment, setEditEquipment] = useState<Equipment | null>(null);
  const [editForm, setEditForm] = useState<EquipmentUpdate>({});

  const { data: equipment, isLoading } = useQuery({
    queryKey: ['equipment', 'list'],
    queryFn: listEquipment,
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/equipment/${id}`),
    onSuccess: (_data, deletedId) => {
      setDeleteError(null);
      queryClient.invalidateQueries({ queryKey: ['equipment', 'list'] });
      queryClient.invalidateQueries({ queryKey: ['equipment', 'detail', deletedId] });
    },
    onError: (error: any) => {
      const msg = error?.response?.data?.detail || 'Error al eliminar equipo';
      setDeleteError(msg);
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: EquipmentUpdate }) =>
      updateEquipment(id, data),
    onSuccess: (_data, updated) => {
      queryClient.invalidateQueries({ queryKey: ['equipment', 'list'] });
      queryClient.invalidateQueries({ queryKey: ['equipment', 'detail', updated.id] });
      setEditOpen(false);
      setEditEquipment(null);
    },
    onError: (error: any) => {
      const msg = error?.response?.data?.detail || 'Error al actualizar equipo';
      alert(msg);
    },
  });

  const handleDelete = (id: string, name: string) => {
    if (confirm(`Eliminar ${name}?`)) {
      deleteMutation.mutate(id);
    }
  };

  const handleEditOpen = (eq: Equipment) => {
    setEditEquipment(eq);
    setEditForm({
      brand: eq.brand,
      model: eq.model,
      serial_number: eq.serial_number,
      equipment_type: eq.equipment_type,
      hours: eq.hours,
      year: eq.year ?? undefined,
      notes: eq.notes ?? undefined,
    });
    setEditOpen(true);
  };

  const handleEditSave = () => {
    if (!editEquipment) return;
    updateMutation.mutate({ id: editEquipment.id, data: editForm });
  };

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

      {deleteError && (
        <div className="text-red-400 text-sm bg-red-950/50 p-3 rounded border border-red-500/30">
          {deleteError}
          <button onClick={() => setDeleteError(null)} className="ml-2 underline">Cerrar</button>
        </div>
      )}

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
                <div className="flex gap-2 pt-2">
                  <Link to={`/diagnosis?equipment=${eq.id}`} className="flex-1">
                    <Button variant="outline" size="sm" className="w-full">
                      Diagnosticar
                    </Button>
                  </Link>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleEditOpen(eq)}
                  >
                    <Pencil className="h-4 w-4 text-zinc-400" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleDelete(eq.id, `${eq.brand} ${eq.model}`)}
                    disabled={deleteMutation.isPending}
                  >
                    <Trash2 className="h-4 w-4 text-red-400" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Edit Dialog */}
      <Dialog open={editOpen} onClose={() => setEditOpen(false)} title="Editar equipo">
        {editEquipment && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <Label>Marca</Label>
                <Input
                  value={editForm.brand || ''}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                    setEditForm({ ...editForm, brand: e.target.value })
                  }
                />
              </div>
              <div className="space-y-1">
                <Label>Modelo</Label>
                <Input
                  value={editForm.model || ''}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                    setEditForm({ ...editForm, model: e.target.value })
                  }
                />
              </div>
            </div>

            <div className="space-y-1">
              <Label>Numero de serie</Label>
              <Input
                value={editForm.serial_number || ''}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                  setEditForm({ ...editForm, serial_number: e.target.value })
                }
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <Label>Tipo</Label>
                <select
                  value={editForm.equipment_type || ''}
                  onChange={(e) =>
                    setEditForm({ ...editForm, equipment_type: e.target.value })
                  }
                  className="w-full h-10 rounded-md border border-zinc-700 bg-zinc-800 px-3 text-sm text-white"
                >
                  {EQUIPMENT_TYPES.map((t) => (
                    <option key={t.value} value={t.value}>{t.label}</option>
                  ))}
                </select>
              </div>
              <div className="space-y-1">
                <Label>Horas</Label>
                <Input
                  type="number"
                  step="any"
                  value={editForm.hours ?? ''}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                    setEditForm({ ...editForm, hours: parseFloat(e.target.value) || 0 })
                  }
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <Label>Ano</Label>
                <Input
                  type="number"
                  value={editForm.year ?? ''}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                    setEditForm({ ...editForm, year: parseInt(e.target.value) || undefined })
                  }
                />
              </div>
              <div className="space-y-1">
                <Label>Notas</Label>
                <Input
                  value={editForm.notes || ''}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                    setEditForm({ ...editForm, notes: e.target.value })
                  }
                />
              </div>
            </div>

            <div className="flex gap-3 pt-2">
              <Button
                onClick={handleEditSave}
                disabled={updateMutation.isPending}
                className="flex-1"
              >
                {updateMutation.isPending ? 'Guardando...' : 'Guardar'}
              </Button>
              <Button variant="outline" onClick={() => setEditOpen(false)}>
                Cancelar
              </Button>
            </div>
          </div>
        )}
      </Dialog>
    </div>
  );
}
