import { Link, Outlet, useLocation } from 'react-router';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import { Wrench, LayoutDashboard, Truck, Stethoscope, AlertTriangle, LogOut } from 'lucide-react';

const navItems = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/equipment', label: 'Equipos', icon: Truck },
  { to: '/diagnosis', label: 'Diagnostico', icon: Stethoscope },
  { to: '/fallas', label: 'Fallas', icon: AlertTriangle },
];

export default function Layout() {
  const { logout } = useAuth();
  const location = useLocation();

  return (
    <div className="min-h-screen flex bg-zinc-950">
      <aside className="w-64 bg-zinc-900 border-r border-zinc-800 flex flex-col">
        <div className="p-6 flex items-center gap-3">
          <Wrench className="h-8 w-8 text-yellow-500" />
          <div>
            <h1 className="text-lg font-bold text-white">GECEM</h1>
            <p className="text-xs text-zinc-400">Reports</p>
          </div>
        </div>
        <Separator className="bg-zinc-800" />
        <nav className="flex-1 p-4 space-y-1">
          {navItems.map(({ to, label, icon: Icon }) => {
            const active = location.pathname === to || (to !== '/' && location.pathname.startsWith(to));
            return (
              <Link
                key={to}
                to={to}
                className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
                  active
                    ? 'bg-yellow-500/10 text-yellow-500'
                    : 'text-zinc-400 hover:text-white hover:bg-zinc-800'
                }`}
              >
                <Icon className="h-4 w-4" />
                {label}
              </Link>
            );
          })}
        </nav>
        <div className="p-4">
          <Separator className="bg-zinc-800 mb-4" />
          <Button
            variant="ghost"
            className="w-full justify-start text-zinc-400 hover:text-red-400"
            onClick={logout}
          >
            <LogOut className="h-4 w-4 mr-3" />
            Cerrar sesion
          </Button>
        </div>
      </aside>
      <main className="flex-1 p-8 overflow-auto">
        <Outlet />
      </main>
    </div>
  );
}
