import { BrowserRouter, Route, Routes } from 'react-router-dom';
import { AuthProvider } from './auth/AuthContext';
import ProtectedRoute from './auth/ProtectedRoute';
import StudentRoute from './auth/StudentRoute';
import AdminRoute from './auth/AdminRoute';
import NavBar from './components/NavBar';
import Home from './pages/Home';
import Plans, { GeneratePlan } from './pages/Plans';
import Profile from './pages/Profile';
import Register from './pages/Register';
import SignIn from './pages/SignIn';
import CatalogImport from './pages/CatalogImport';
import Courses from './pages/Courses';
import './auth/auth.css';

export function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <NavBar />
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/signin" element={<SignIn />} />
          <Route path="/register" element={<Register />} />

          {/* Any signed-in user */}
          <Route element={<ProtectedRoute />}>
            <Route path="/courses" element={<Courses />} />
          </Route>

          {/* Students only */}
          <Route element={<StudentRoute />}>
            <Route path="/profile" element={<Profile />} />
            <Route path="/plans" element={<Plans />} />
            <Route path="/plans/generate" element={<GeneratePlan />} />
            <Route path="/plans/:planId" element={<Plans />} />
          </Route>

          {/* Admins only */}
          <Route element={<AdminRoute />}>
            <Route path="/catalog/import" element={<CatalogImport />} />
          </Route>

          <Route path="*" element={<p style={{ textAlign: 'center', marginTop: '3rem' }}>Page not found</p>} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
