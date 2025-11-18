import React, { useState, useEffect } from 'react';
import { 
  Card, 
  Form, 
  Select, 
  InputNumber, 
  Switch, 
  Button, 
  message, 
  Spin, 
  Row, 
  Col, 
  Divider,
  Alert,
  Tooltip,
  Modal
} from 'antd';
import { 
  SettingOutlined, 
  ClockCircleOutlined, 
  WifiOutlined,
  SaveOutlined,
  InfoCircleOutlined,
  ThunderboltOutlined,
  UserOutlined,
  DatabaseOutlined
} from '@ant-design/icons';
import { radiusAPI } from '../services/api';

const { Option } = Select;

const RadiusSettings = () => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [settings, setSettings] = useState(null);
  const [applyToAll, setApplyToAll] = useState(false);

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      setLoading(true);
      const response = await radiusAPI.getSettings();
      
      if (response.data.success) {
        setSettings(response.data.settings);
        form.setFieldsValue(response.data.settings);
      }
    } catch (error) {
      console.error('Error loading settings:', error);
      message.error('Failed to load RADIUS settings');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async (values) => {
    if (applyToAll) {
      Modal.confirm({
        title: 'Apply to All Users',
        content: 'This will update settings for ALL existing RADIUS users. Are you sure?',
        okText: 'Yes, Apply to All',
        okType: 'danger',
        cancelText: 'Cancel',
        onOk: () => saveSettings(values, true)
      });
    } else {
      await saveSettings(values, false);
    }
  };

  const saveSettings = async (values, applyAll) => {
    try {
      setSaving(true);
      
      const payload = {
        ...values,
        apply_to_all: applyAll
      };
      
      const response = await radiusAPI.updateSettings(payload);
      
      if (response.data.success) {
        message.success('RADIUS settings saved successfully');
        setApplyToAll(false);
        loadSettings();
      } else {
        message.error(response.data.message || 'Failed to save settings');
      }
    } catch (error) {
      console.error('Error saving settings:', error);
      if (error.response?.status === 403) {
        message.error('Only superadmin can change these settings');
      } else {
        message.error('Failed to save RADIUS settings');
      }
    } finally {
      setSaving(false);
    }
  };

  const formatDuration = (seconds) => {
    if (seconds < 3600) return `${seconds / 60} minutes`;
    if (seconds < 86400) return `${seconds / 3600} hours`;
    return `${seconds / 86400} days`;
  };

  if (loading) {
    return (
      <div style={{ padding: '24px', textAlign: 'center' }}>
        <Spin size="large" />
        <p style={{ marginTop: '16px' }}>Loading RADIUS settings...</p>
      </div>
    );
  }

  return (
    <div style={{ padding: '24px' }}>
      <div style={{ marginBottom: '24px' }}>
        <h2>
          <SettingOutlined style={{ marginRight: '8px' }} />
          RADIUS Server Settings
        </h2>
        <p style={{ color: '#666' }}>
          Configure default session timeouts, bandwidth limits, and other RADIUS parameters for WiFi users.
        </p>
      </div>

      <Form
        form={form}
        layout="vertical"
        onFinish={handleSave}
        initialValues={settings}
      >
        <Row gutter={24}>
          {/* Session Settings */}
          <Col xs={24} lg={12}>
            <Card 
              title={
                <span>
                  <ClockCircleOutlined style={{ marginRight: '8px' }} />
                  Session Settings
                </span>
              }
              style={{ marginBottom: '24px' }}
            >
              <Form.Item
                name="default_session_timeout"
                label={
                  <span>
                    Default Session Duration
                    <Tooltip title="How long a user can stay connected before needing to re-authenticate">
                      <InfoCircleOutlined style={{ marginLeft: '8px', color: '#999' }} />
                    </Tooltip>
                  </span>
                }
                rules={[{ required: true, message: 'Please select session duration' }]}
              >
                <Select size="large">
                  {settings?.timeout_options?.map(opt => (
                    <Option key={opt.value} value={opt.value}>
                      {opt.label}
                    </Option>
                  ))}
                </Select>
              </Form.Item>

              <Form.Item
                name="max_session_timeout"
                label={
                  <span>
                    Maximum Session Duration
                    <Tooltip title="Maximum allowed session time (for per-user overrides)">
                      <InfoCircleOutlined style={{ marginLeft: '8px', color: '#999' }} />
                    </Tooltip>
                  </span>
                }
              >
                <Select size="large">
                  <Option value={3600}>1 hour</Option>
                  <Option value={7200}>2 hours</Option>
                  <Option value={14400}>4 hours</Option>
                  <Option value={28800}>8 hours</Option>
                  <Option value={43200}>12 hours</Option>
                  <Option value={86400}>24 hours</Option>
                </Select>
              </Form.Item>

              <Form.Item
                name="idle_timeout"
                label={
                  <span>
                    Idle Timeout
                    <Tooltip title="Disconnect user after this period of inactivity">
                      <InfoCircleOutlined style={{ marginLeft: '8px', color: '#999' }} />
                    </Tooltip>
                  </span>
                }
              >
                <Select size="large">
                  <Option value={300}>5 minutes</Option>
                  <Option value={600}>10 minutes</Option>
                  <Option value={900}>15 minutes</Option>
                  <Option value={1800}>30 minutes</Option>
                  <Option value={3600}>1 hour</Option>
                  <Option value={0}>Disabled</Option>
                </Select>
              </Form.Item>
            </Card>
          </Col>

          {/* Bandwidth Settings */}
          <Col xs={24} lg={12}>
            <Card 
              title={
                <span>
                  <ThunderboltOutlined style={{ marginRight: '8px' }} />
                  Bandwidth Limits
                </span>
              }
              style={{ marginBottom: '24px' }}
            >
              <Form.Item
                name="default_bandwidth_down"
                label={
                  <span>
                    Download Speed Limit
                    <Tooltip title="Maximum download speed for users (0 = unlimited)">
                      <InfoCircleOutlined style={{ marginLeft: '8px', color: '#999' }} />
                    </Tooltip>
                  </span>
                }
              >
                <Select size="large">
                  {settings?.bandwidth_options?.map(opt => (
                    <Option key={opt.value} value={opt.value}>
                      {opt.label}
                    </Option>
                  ))}
                </Select>
              </Form.Item>

              <Form.Item
                name="default_bandwidth_up"
                label={
                  <span>
                    Upload Speed Limit
                    <Tooltip title="Maximum upload speed for users (0 = unlimited)">
                      <InfoCircleOutlined style={{ marginLeft: '8px', color: '#999' }} />
                    </Tooltip>
                  </span>
                }
              >
                <Select size="large">
                  {settings?.bandwidth_options?.map(opt => (
                    <Option key={opt.value} value={opt.value}>
                      {opt.label}
                    </Option>
                  ))}
                </Select>
              </Form.Item>

              <Alert
                message="Bandwidth Control"
                description="Bandwidth limits use WISPr attributes. Make sure your RADIUS server and Omada controller support these attributes."
                type="info"
                showIcon
                style={{ marginTop: '16px' }}
              />
            </Card>
          </Col>

          {/* User Limits */}
          <Col xs={24} lg={12}>
            <Card 
              title={
                <span>
                  <UserOutlined style={{ marginRight: '8px' }} />
                  User Limits
                </span>
              }
              style={{ marginBottom: '24px' }}
            >
              <Form.Item
                name="max_concurrent_sessions"
                label={
                  <span>
                    Max Concurrent Sessions
                    <Tooltip title="Maximum number of devices a user can connect simultaneously">
                      <InfoCircleOutlined style={{ marginLeft: '8px', color: '#999' }} />
                    </Tooltip>
                  </span>
                }
              >
                <InputNumber 
                  min={1} 
                  max={10} 
                  size="large" 
                  style={{ width: '100%' }}
                />
              </Form.Item>

              <Form.Item
                name="allow_multiple_devices"
                label="Allow Multiple Devices"
                valuePropName="checked"
              >
                <Switch checkedChildren="Yes" unCheckedChildren="No" />
              </Form.Item>
            </Card>
          </Col>

          {/* Data Limits */}
          <Col xs={24} lg={12}>
            <Card 
              title={
                <span>
                  <DatabaseOutlined style={{ marginRight: '8px' }} />
                  Data Limits
                </span>
              }
              style={{ marginBottom: '24px' }}
            >
              <Form.Item
                name="daily_data_limit"
                label={
                  <span>
                    Daily Data Limit (MB)
                    <Tooltip title="Maximum data usage per day (0 = unlimited)">
                      <InfoCircleOutlined style={{ marginLeft: '8px', color: '#999' }} />
                    </Tooltip>
                  </span>
                }
              >
                <InputNumber 
                  min={0} 
                  max={100000} 
                  size="large" 
                  style={{ width: '100%' }}
                  placeholder="0 = Unlimited"
                />
              </Form.Item>

              <Form.Item
                name="monthly_data_limit"
                label={
                  <span>
                    Monthly Data Limit (MB)
                    <Tooltip title="Maximum data usage per month (0 = unlimited)">
                      <InfoCircleOutlined style={{ marginLeft: '8px', color: '#999' }} />
                    </Tooltip>
                  </span>
                }
              >
                <InputNumber 
                  min={0} 
                  max={1000000} 
                  size="large" 
                  style={{ width: '100%' }}
                  placeholder="0 = Unlimited"
                />
              </Form.Item>

              <Alert
                message="Note"
                description="Data limits require accounting to be properly configured in FreeRADIUS."
                type="warning"
                showIcon
                style={{ marginTop: '16px' }}
              />
            </Card>
          </Col>
        </Row>

        <Divider />

        {/* Save Options */}
        <Card style={{ marginBottom: '24px' }}>
          <Row align="middle" justify="space-between">
            <Col>
              <Form.Item style={{ marginBottom: 0 }}>
                <Switch 
                  checked={applyToAll}
                  onChange={setApplyToAll}
                  style={{ marginRight: '8px' }}
                />
                <span>
                  Apply changes to all existing users
                  <Tooltip title="If enabled, these settings will be applied to all existing RADIUS users. Otherwise, only new users will get these defaults.">
                    <InfoCircleOutlined style={{ marginLeft: '8px', color: '#999' }} />
                  </Tooltip>
                </span>
              </Form.Item>
            </Col>
            <Col>
              <Button 
                type="primary" 
                htmlType="submit" 
                size="large"
                icon={<SaveOutlined />}
                loading={saving}
              >
                Save Settings
              </Button>
            </Col>
          </Row>
        </Card>

        {/* Current Settings Summary */}
        {settings && (
          <Card 
            title="Current Configuration Summary" 
            size="small"
            style={{ background: '#f5f5f5' }}
          >
            <Row gutter={16}>
              <Col span={8}>
                <p><strong>Session Duration:</strong> {formatDuration(settings.default_session_timeout)}</p>
              </Col>
              <Col span={8}>
                <p><strong>Download Limit:</strong> {settings.default_bandwidth_down === 0 ? 'Unlimited' : `${settings.default_bandwidth_down} Kbps`}</p>
              </Col>
              <Col span={8}>
                <p><strong>Upload Limit:</strong> {settings.default_bandwidth_up === 0 ? 'Unlimited' : `${settings.default_bandwidth_up} Kbps`}</p>
              </Col>
            </Row>
          </Card>
        )}
      </Form>
    </div>
  );
};

export default RadiusSettings;
