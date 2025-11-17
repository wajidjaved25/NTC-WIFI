import { Layout, Menu } from 'antd'
import {
  DashboardOutlined,
  SettingOutlined,
  FileTextOutlined,
  PictureOutlined,
  SkinOutlined,
  TeamOutlined,
  LogoutOutlined,
  WifiOutlined,
} from '@ant-design/icons'
import { useNavigate, useLocation } from 'react-router-dom'
import './MainLayout.css'

const { Header, Sider, Content, Footer } = Layout

function MainLayout({ children, user, onLogout }) {
  const navigate = useNavigate()
  const location = useLocation()

  const getMenuItems = () => {
    const items = [
      {
        key: '/dashboard',
        icon: <DashboardOutlined />,
        label: 'Dashboard',
      },
    ]

    // Omada settings - superadmin & admin only
    if (['superadmin', 'admin'].includes(user.role)) {
      items.push({
        key: '/omada',
        icon: <SettingOutlined />,
        label: 'Omada Settings',
      })
    }

    // Records - all roles
    items.push({
      key: '/records',
      icon: <FileTextOutlined />,
      label: 'Records',
    })

    // Advertisements - superadmin, admin, ads_user
    if (['superadmin', 'admin', 'ads_user'].includes(user.role)) {
      items.push({
        key: '/advertisements',
        icon: <PictureOutlined />,
        label: 'Advertisements',
      })
    }

    // Portal Design - superadmin & admin only
    if (['superadmin', 'admin'].includes(user.role)) {
      items.push({
        key: '/portal-design',
        icon: <SkinOutlined />,
        label: 'Portal Design',
      })
    }

    // RADIUS Sessions - superadmin & admin only
    if (['superadmin', 'admin'].includes(user.role)) {
      items.push({
        key: '/radius-sessions',
        icon: <WifiOutlined />,
        label: 'Active Sessions',
      })
    }

    // Admin Management - superadmin only
    if (user.role === 'superadmin') {
      items.push({
        key: '/admin-management',
        icon: <TeamOutlined />,
        label: 'Admin Management',
      })
    }

    return items
  }

  const handleMenuClick = ({ key }) => {
    navigate(key)
  }

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider
        breakpoint="lg"
        collapsedWidth="0"
        theme="dark"
      >
        <div className="logo">NTC WiFi Admin</div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[location.pathname]}
          items={getMenuItems()}
          onClick={handleMenuClick}
        />
      </Sider>
      
      <Layout>
        <Header className="site-layout-header">
          <div className="header-content">
            <div className="header-title">
              {location.pathname === '/dashboard' && 'Dashboard'}
              {location.pathname === '/omada' && 'Omada Controller Settings'}
              {location.pathname === '/records' && 'Session Records'}
              {location.pathname === '/advertisements' && 'Advertisement Management'}
              {location.pathname === '/portal-design' && 'Portal Design'}
              {location.pathname === '/radius-sessions' && 'Active RADIUS Sessions'}
              {location.pathname === '/admin-management' && 'Admin Management'}
            </div>
            <div className="header-user">
              <span className="user-name">{user.full_name || user.username}</span>
              <span className="user-role">({user.role})</span>
              <LogoutOutlined 
                className="logout-icon" 
                onClick={onLogout}
                title="Logout"
              />
            </div>
          </div>
        </Header>
        
        <Content style={{ margin: '24px 16px 0' }}>
          <div className="site-layout-background">
            {children}
          </div>
        </Content>
        
        <Footer style={{ 
          textAlign: 'center', 
          background: '#001529',
          color: 'rgba(255, 255, 255, 0.65)',
          padding: '20px 50px'
        }}>
          <div style={{ marginBottom: '16px' }}>
            © {new Date().getFullYear()} NTC WiFi Admin Portal. All rights reserved.
          </div>
          <div style={{ 
            display: 'flex', 
            alignItems: 'center', 
            justifyContent: 'center',
            gap: '12px',
            fontSize: '13px'
          }}>
            <span>In collaboration with</span>
            <a 
              href="https://www.superapp.pk" 
              target="_blank" 
              rel="noopener noreferrer"
              style={{ display: 'inline-block', lineHeight: 0 }}
            >
              <img 
                src="/SuperApp-white-logo.png" 
                alt="SuperApp - The Digital Powerhouse" 
                style={{ height: '28px', width: 'auto', verticalAlign: 'middle' }}
                onError={(e) => { e.target.style.display = 'none'; }}
              />
            </a>
          </div>
        </Footer>
      </Layout>
    </Layout>
  )
}

export default MainLayout
