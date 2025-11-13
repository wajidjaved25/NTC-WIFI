import { useState } from 'react'
import { Card, Form, Input, Button, Tabs, message, Space, Typography } from 'antd'
import { UserOutlined, LockOutlined, MobileOutlined, SafetyOutlined } from '@ant-design/icons'
import { authAPI } from '../services/api'
import './Login.css'

const { Title } = Typography

function Login({ onLogin }) {
  const [loading, setLoading] = useState(false)
  const [otpSent, setOtpSent] = useState(false)
  const [mobile, setMobile] = useState('')

  const handlePasswordLogin = async (values) => {
    setLoading(true)
    try {
      const response = await authAPI.login(values.username, values.password)
      const { access_token, role, username, full_name } = response.data
      
      localStorage.setItem('token', access_token)
      localStorage.setItem('user', JSON.stringify({ role, username, full_name }))
      
      message.success('Login successful!')
      onLogin({ role, username, full_name })
    } catch (error) {
      message.error(error.response?.data?.detail || 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  const handleRequestOTP = async (values) => {
    setLoading(true)
    try {
      await authAPI.requestOTP(values.mobile)
      setMobile(values.mobile)
      setOtpSent(true)
      message.success('OTP sent to your mobile')
    } catch (error) {
      message.error(error.response?.data?.detail || 'Failed to send OTP')
    } finally {
      setLoading(false)
    }
  }

  const handleVerifyOTP = async (values) => {
    setLoading(true)
    try {
      const response = await authAPI.verifyOTP(mobile, values.otp)
      const { access_token, role, username, full_name } = response.data
      
      localStorage.setItem('token', access_token)
      localStorage.setItem('user', JSON.stringify({ role, username, full_name }))
      
      message.success('Login successful!')
      onLogin({ role, username, full_name })
    } catch (error) {
      message.error(error.response?.data?.detail || 'Invalid OTP')
    } finally {
      setLoading(false)
    }
  }

  const tabItems = [
    {
      key: 'password',
      label: 'Admin Login',
      children: (
        <Form
          name="password_login"
          onFinish={handlePasswordLogin}
          size="large"
        >
          <Form.Item
            name="username"
            rules={[{ required: true, message: 'Please enter username' }]}
          >
            <Input 
              prefix={<UserOutlined />} 
              placeholder="Username" 
            />
          </Form.Item>

          <Form.Item
            name="password"
            rules={[{ required: true, message: 'Please enter password' }]}
          >
            <Input.Password 
              prefix={<LockOutlined />} 
              placeholder="Password" 
            />
          </Form.Item>

          <Form.Item>
            <Button 
              type="primary" 
              htmlType="submit" 
              loading={loading}
              block
            >
              Login
            </Button>
          </Form.Item>
        </Form>
      ),
    },
    {
      key: 'otp',
      label: 'OTP Login',
      children: !otpSent ? (
        <Form
          name="otp_request"
          onFinish={handleRequestOTP}
          size="large"
        >
          <Form.Item
            name="mobile"
            rules={[
              { required: true, message: 'Please enter mobile number' },
              { pattern: /^[0-9]{11}$/, message: 'Enter valid 11-digit mobile number' }
            ]}
          >
            <Input 
              prefix={<MobileOutlined />} 
              placeholder="Mobile Number (03XXXXXXXXX)" 
              maxLength={11}
            />
          </Form.Item>

          <Form.Item>
            <Button 
              type="primary" 
              htmlType="submit" 
              loading={loading}
              block
            >
              Send OTP
            </Button>
          </Form.Item>
        </Form>
      ) : (
        <Space direction="vertical" style={{ width: '100%' }} size="large">
          <div style={{ textAlign: 'center' }}>
            OTP sent to {mobile}
          </div>
          <Form
            name="otp_verify"
            onFinish={handleVerifyOTP}
            size="large"
          >
            <Form.Item
              name="otp"
              rules={[
                { required: true, message: 'Please enter OTP' },
                { len: 6, message: 'OTP must be 6 digits' }
              ]}
            >
              <Input 
                prefix={<SafetyOutlined />} 
                placeholder="Enter 6-digit OTP" 
                maxLength={6}
              />
            </Form.Item>

            <Form.Item>
              <Button 
                type="primary" 
                htmlType="submit" 
                loading={loading}
                block
              >
                Verify OTP
              </Button>
            </Form.Item>

            <Button 
              type="link" 
              onClick={() => setOtpSent(false)}
              block
            >
              Use different number
            </Button>
          </Form>
        </Space>
      ),
    },
  ]

  return (
    <div className="login-container">
      <Card className="login-card" bordered={false}>
        <div className="login-header">
          <Title level={2}>NTC WiFi Admin Portal</Title>
          <p>Please login to continue</p>
        </div>
        
        <Tabs defaultActiveKey="password" items={tabItems} centered />
      </Card>
    </div>
  )
}

export default Login
