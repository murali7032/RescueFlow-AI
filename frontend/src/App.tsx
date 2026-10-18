import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { DemoRoleProvider } from "./context/DemoRoleContext";
import { AppShell } from "./layout/AppShell";
import AdminDashboardPage from "./pages/AdminDashboardPage";
import DashboardPage from "./pages/DashboardPage";
import DonorWorkspacePage from "./pages/DonorWorkspacePage";
import RecipientWorkspacePage from "./pages/RecipientWorkspacePage";

export default function App() {
  return (
    <DemoRoleProvider>
      <BrowserRouter>
        <Routes>
          <Route element={<AppShell />}>
            <Route index element={<DashboardPage />} />
            <Route path="donor" element={<DonorWorkspacePage />} />
            <Route path="recipient" element={<RecipientWorkspacePage />} />
            <Route path="admin" element={<AdminDashboardPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </DemoRoleProvider>
  );
}
