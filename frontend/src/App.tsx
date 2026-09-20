import { BrowserRouter, Routes, Route } from 'react-router';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider } from '@/contexts/AuthContext';
import ProtectedRoute from '@/components/ProtectedRoute';
import Layout from '@/components/Layout';
import LoginPage from '@/pages/LoginPage';
import RegisterPage from '@/pages/RegisterPage';
import DashboardPage from '@/pages/DashboardPage';
import EquipmentListPage from '@/pages/EquipmentListPage';
import EquipmentCreatePage from '@/pages/EquipmentCreatePage';
import DiagnosisPage from '@/pages/DiagnosisPage';
import DiagnosisResultPage from '@/pages/DiagnosisResultPage';
import FallaPage from '@/pages/FallaPage';
import FallasPage from '@/pages/FallasPage';
import FallaDetailPage from '@/pages/FallaDetailPage';
import RefaccionesPage from '@/pages/RefaccionesPage';
import CotizacionPage from '@/pages/CotizacionPage';
import CotizacionDetailPage from '@/pages/CotizacionDetailPage';
import ReparacionPage from '@/pages/ReparacionPage';
import ReporteClientePage from '@/pages/ReporteClientePage';

const queryClient = new QueryClient();

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
            <Route
              element={
                <ProtectedRoute>
                  <Layout />
                </ProtectedRoute>
              }
            >
              <Route path="/" element={<DashboardPage />} />
              <Route path="/equipment" element={<EquipmentListPage />} />
              <Route path="/equipment/new" element={<EquipmentCreatePage />} />
              <Route path="/diagnosis" element={<DiagnosisPage />} />
              <Route path="/diagnosis/result" element={<DiagnosisResultPage />} />
              <Route path="/falla" element={<FallaPage />} />
              <Route path="/fallas" element={<FallasPage />} />
              <Route path="/fallas/:id" element={<FallaDetailPage />} />
              <Route path="/fallas/:id/refacciones" element={<RefaccionesPage />} />
              <Route path="/fallas/:id/cotizacion" element={<CotizacionPage />} />
              <Route path="/cotizaciones/:id" element={<CotizacionDetailPage />} />
              <Route path="/fallas/:id/reparacion" element={<ReparacionPage />} />
              <Route path="/fallas/:id/reporte" element={<ReporteClientePage />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  );
}
