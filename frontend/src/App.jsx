import { useState, useEffect } from 'react'
import { Routes, Route, Navigate, useNavigate } from 'react-router-dom'
import { Spin } from 'antd'
import MainLayout from './components/Layout/MainLayout'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import OmadaSettings from './pages/OmadaSettings'
import Records from './pages/Records'
import Advertisements from './pages/Advertisements'
import PortalDesign from './pages/PortalDesign'
import AdminManagement from './pages/AdminManagement'
import UserManagement from './pages/UserManagement'
import RadiusSessions from './pages/RadiusSessions'
import RadiusSettings from './pages/RadiusSettings'
import IPDRReports from './pages/IPDRReports'
import SiteManagement from './pages/SiteManagement'
import PakAppUsers from './pages/PakAppUsers'
import { authAPI } from './services/api'
import './App.css'

function App() {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  useEffect(() => {
    checkAuth()
  }, [])

  const checkAuth = async () => {
    const token = localStorage.getItem('token')
    if (!token) {
      setLoading(false)
      return
    }

    try {
      const response = await authAPI.getMe()
      setUser(response.data)
    } catch (error) {
      localStorage.removeItem('token')
      localStorage.removeItem('user')
    } finally {
      setLoading(false)
    }
  }

  const handleLogin = (userData) => {
    setUser(userData)
    navigate('/dashboard')
  }

  const handleLogout = () => {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    setUser(null)
    navigate('/login')
  }

  if (loading) {
    return (
      <div style={{ 
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'center', 
        height: '100vh' 
      }}>
        <Spin size="large" />
      </div>
    )
  }

  return (
    <Routes>
      <Route 
        path="/login" 
        element={
          !user ? <Login onLogin={handleLogin} /> : <Navigate to="/dashboard" />
        } 
      />
      
      <Route 
        path="/" 
        element={
          user ? (
            <MainLayout user={user} onLogout={handleLogout}>
              <Dashboard />
            </MainLayout>
          ) : (
            <Navigate to="/login" />
          )
        } 
      />

      <Route 
        path="/dashboard" 
        element={
          user ? (
            <MainLayout user={user} onLogout={handleLogout}>
              <Dashboard />
            </MainLayout>
          ) : (
            <Navigate to="/login" />
          )
        } 
      />

      <Route 
        path="/omada" 
        element={
          user && ['superadmin', 'admin'].includes(user.role) ? (
            <MainLayout user={user} onLogout={handleLogout}>
              <OmadaSettings />
            </MainLayout>
          ) : (
            <Navigate to="/dashboard" />
          )
        } 
      />

      <Route 
        path="/records" 
        element={
          user ? (
            <MainLayout user={user} onLogout={handleLogout}>
              <Records />
            </MainLayout>
          ) : (
            <Navigate to="/login" />
          )
        } 
      />

      <Route 
        path="/advertisements" 
        element={
          user && ['superadmin', 'admin', 'ads_user'].includes(user.role) ? (
            <MainLayout user={user} onLogout={handleLogout}>
              <Advertisements />
            </MainLayout>
          ) : (
            <Navigate to="/dashboard" />
          )
        } 
      />

      <Route 
        path="/portal-design" 
        element={
          user && ['superadmin', 'admin'].includes(user.role) ? (
            <MainLayout user={user} onLogout={handleLogout}>
              <PortalDesign />
            </MainLayout>
          ) : (
            <Navigate to="/dashboard" />
          )
        } 
      />

      <Route 
        path="/admin-management" 
        element={
          user && ['superadmin', 'admin'].includes(user.role) ? (
            <MainLayout user={user} onLogout={handleLogout}>
              <AdminManagement />
            </MainLayout>
          ) : (
            <Navigate to="/dashboard" />
          )
        } 
      />

      <Route 
        path="/user-management" 
        element={
          user && ['superadmin', 'admin'].includes(user.role) ? (
            <MainLayout user={user} onLogout={handleLogout}>
              <UserManagement />
            </MainLayout>
          ) : (
            <Navigate to="/dashboard" />
          )
        } 
      />

      <Route 
        path="/radius-sessions" 
        element={
          user && ['superadmin', 'admin'].includes(user.role) ? (
            <MainLayout user={user} onLogout={handleLogout}>
              <RadiusSessions />
            </MainLayout>
          ) : (
            <Navigate to="/dashboard" />
          )
        } 
      />

      <Route 
        path="/radius-settings" 
        element={
          user && ['superadmin', 'admin'].includes(user.role) ? (
            <MainLayout user={user} onLogout={handleLogout}>
              <RadiusSettings />
            </MainLayout>
          ) : (
            <Navigate to="/dashboard" />
          )
        } 
      />

      <Route 
        path="/ipdr-reports" 
        element={
          user && ['superadmin', 'admin', 'ipdr_viewer'].includes(user.role) ? (
            <MainLayout user={user} onLogout={handleLogout}>
              <IPDRReports />
            </MainLayout>
          ) : (
            <Navigate to="/dashboard" />
          )
        } 
      />

      <Route 
        path="/sites" 
        element={
          user && ['superadmin', 'admin'].includes(user.role) ? (
            <MainLayout user={user} onLogout={handleLogout}>
              <SiteManagement />
            </MainLayout>
          ) : (
            <Navigate to="/dashboard" />
          )
        } 
      />

      <Route 
        path="/pakapp-users" 
        element={
          user && ['superadmin', 'admin'].includes(user.role) ? (
            <MainLayout user={user} onLogout={handleLogout}>
              <PakAppUsers />
            </MainLayout>
          ) : (
            <Navigate to="/dashboard" />
          )
        } 
      />

      <Route path="*" element={<Navigate to="/dashboard" />} />
    </Routes>
  )
}

export default App
