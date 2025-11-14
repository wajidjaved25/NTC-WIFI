import React, { useState, useEffect } from 'react';
import {
  Form,
  Input,
  InputNumber,
  Switch,
  Button,
  Card,
  Row,
  Col,
  Divider,
  message,
  Space,
  Tooltip,
  Alert,
  Spin,
} from 'antd';
import {
  SaveOutlined,
  ReloadOutlined,
  ApiOutlined,
  InfoCircleOutlined,
  SyncOutlined,
} from '@ant-design/icons';
import './OmadaConfigForm.css';

const OmadaConfigForm = ({ onSave, onTest, initialData, loading }) => {
  const [form] = Form.useForm();
  const [testing, setTesting] = useState(false);
  const [detecting, setDetecting] = useState(false);
  const [hasChanges, setHasChanges] = useState(false);

  useEffect(() => {
    if (initialData) {
      form.setFieldsValue(initialData);
    }
  }, [initialData, form]);

  const handleValuesChange = () => {
    setHasChanges(true);
  };

  const handleTestConnection = async () => {
    try {
      const values = await form.validateFields(['controller_url', 'username', 'password_encrypted']);
      setTesting(true);
      await onTest(values);
      message.success('Connection successful!');
    } catch (error) {
      if (error.errorFields) {
        message.error('Please fill in required fields');
      } else {
        message.error('Connection failed: ' + (error.message || 'Unknown error'));
      }
    } finally {
      setTesting(false);
    }
  };

  const handleDetectControllerId = async () => {
    try {
      const values = await form.validateFields(['controller_url', 'username', 'password_encrypted']);
      setDetecting(true);
      
      const response = await fetch('http://localhost:8000/api/omada/detect-controller-id', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
        body: JSON.stringify(values),
      });
      
      const result = await response.json();
      
      if (result.success && result.controller_id) {
        form.setFieldsValue({ controller_id: result.controller_id });
        message.success('Controller ID detected: ' + result.controller_id);
        setHasChanges(true);
      } else {
        message.warning('Could not auto-detect Controller ID. Please enter it manually.');
      }
    } catch (error) {
      message.error('Failed to detect Controller ID');
    } finally {
      setDetecting(false);
    }
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      await onSave(values);
      setHasChanges(false);
      message.success('Configuration saved successfully!');
    } catch (error) {
      if (error.errorFields) {
        message.error('Please check the form for errors');
      } else {
        message.error('Failed to save configuration');
      }
    }
  };

  const handleReset = () => {
    form.resetFields();
    setHasChanges(false);
  };

  return (
    <Spin spinning={loading}>
      <Form
        form={form}
        layout="vertical"
        onValuesChange={handleValuesChange}
        initialValues={{
          session_timeout: 3600,
          idle_timeout: 600,
          daily_time_limit: 7200,
          max_daily_sessions: 3,
          enable_rate_limiting: true,
          enable_mac_filtering: false,
          auth_type: 'external',
          site_id: 'Default',
        }}
      >
        {hasChanges && (
          <Alert
            message="You have unsaved changes"
            type="warning"
            showIcon
            style={{ marginBottom: 16 }}
          />
        )}

        {/* Controller Connection */}
        <Card title="Controller Connection" className="config-card">
          <Row gutter={16}>
            <Col span={24}>
              <Form.Item
                label="Configuration Name"
                name="config_name"
                rules={[{ required: true, message: 'Please enter configuration name' }]}
              >
                <Input placeholder="e.g., Main Office Controller" />
              </Form.Item>
            </Col>
            <Col xs={24} md={12}>
              <Form.Item
                label={
                  <span>
                    Controller URL{' '}
                    <Tooltip title="Full URL including protocol (https://) and port">
                      <InfoCircleOutlined />
                    </Tooltip>
                  </span>
                }
                name="controller_url"
                rules={[
                  { required: true, message: 'Please enter controller URL' },
                  { type: 'url', message: 'Please enter a valid URL' },
                ]}
              >
                <Input placeholder="https://10.2.49.26:8043" />
              </Form.Item>
            </Col>
            <Col xs={24} md={12}>
              <Form.Item
                label={
                  <span>
                    Controller ID (omadacId){' '}
                    <Tooltip title="Auto-detect or manually enter the Omada Controller ID">
                      <InfoCircleOutlined />
                    </Tooltip>
                  </span>
                }
                name="controller_id"
              >
                <Input placeholder="e.g., 1a2b3c4d5e6f7g8h" />
              </Form.Item>
            </Col>
            <Col span={24}>
              <Button
                icon={<SyncOutlined />}
                onClick={handleDetectControllerId}
                loading={detecting}
                style={{ marginBottom: 16 }}
              >
                Auto-Detect Controller ID
              </Button>
            </Col>
            <Col xs={24} md={12}>
              <Form.Item
                label="Site ID"
                name="site_id"
                rules={[{ required: true, message: 'Please enter site ID' }]}
              >
                <Input placeholder="Default" />
              </Form.Item>
            </Col>
            <Col xs={24} md={12}>
              <Form.Item
                label="Username"
                name="username"
                rules={[{ required: true, message: 'Please enter username' }]}
              >
                <Input placeholder="admin" />
              </Form.Item>
            </Col>
            <Col xs={24} md={12}>
              <Form.Item
                label="Password"
                name="password_encrypted"
                rules={[{ required: true, message: 'Please enter password' }]}
              >
                <Input.Password placeholder="Enter controller password" />
              </Form.Item>
            </Col>
            <Col span={24}>
              <Button
                icon={<ApiOutlined />}
                onClick={handleTestConnection}
                loading={testing}
              >
                Test Connection
              </Button>
            </Col>
          </Row>
        </Card>

        <Divider />

        {/* Session Control */}
        <Card title="Session Control" className="config-card">
          <Row gutter={16}>
            <Col xs={24} md={8}>
              <Form.Item
                label={
                  <span>
                    Session Timeout (seconds){' '}
                    <Tooltip title="Maximum session duration">
                      <InfoCircleOutlined />
                    </Tooltip>
                  </span>
                }
                name="session_timeout"
                rules={[{ required: true, message: 'Please enter session timeout' }]}
              >
                <InputNumber
                  min={60}
                  max={86400}
                  style={{ width: '100%' }}
                  placeholder="3600"
                />
              </Form.Item>
            </Col>
            <Col xs={24} md={8}>
              <Form.Item
                label={
                  <span>
                    Idle Timeout (seconds){' '}
                    <Tooltip title="Disconnect after inactivity">
                      <InfoCircleOutlined />
                    </Tooltip>
                  </span>
                }
                name="idle_timeout"
                rules={[{ required: true, message: 'Please enter idle timeout' }]}
              >
                <InputNumber
                  min={60}
                  max={3600}
                  style={{ width: '100%' }}
                  placeholder="600"
                />
              </Form.Item>
            </Col>
            <Col xs={24} md={8}>
              <Form.Item
                label={
                  <span>
                    Daily Time Limit (seconds){' '}
                    <Tooltip title="Total allowed time per user per day">
                      <InfoCircleOutlined />
                    </Tooltip>
                  </span>
                }
                name="daily_time_limit"
                rules={[{ required: true, message: 'Please enter daily limit' }]}
              >
                <InputNumber
                  min={300}
                  max={86400}
                  style={{ width: '100%' }}
                  placeholder="7200"
                />
              </Form.Item>
            </Col>
            <Col xs={24} md={12}>
              <Form.Item
                label="Max Daily Sessions"
                name="max_daily_sessions"
                rules={[{ required: true, message: 'Please enter max sessions' }]}
              >
                <InputNumber
                  min={1}
                  max={100}
                  style={{ width: '100%' }}
                  placeholder="3"
                />
              </Form.Item>
            </Col>
          </Row>
        </Card>

        <Divider />

        {/* Bandwidth Control */}
        <Card title="Bandwidth Control" className="config-card">
          <Row gutter={16}>
            <Col span={24}>
              <Form.Item
                label="Enable Rate Limiting"
                name="enable_rate_limiting"
                valuePropName="checked"
              >
                <Switch />
              </Form.Item>
            </Col>
            <Col xs={24} md={8}>
              <Form.Item
                label="Upload Limit (kbps)"
                name="bandwidth_limit_up"
                tooltip="Leave empty for no limit"
              >
                <InputNumber
                  min={0}
                  max={1000000}
                  style={{ width: '100%' }}
                  placeholder="0 (unlimited)"
                />
              </Form.Item>
            </Col>
            <Col xs={24} md={8}>
              <Form.Item
                label="Download Limit (kbps)"
                name="bandwidth_limit_down"
                tooltip="Leave empty for no limit"
              >
                <InputNumber
                  min={0}
                  max={1000000}
                  style={{ width: '100%' }}
                  placeholder="0 (unlimited)"
                />
              </Form.Item>
            </Col>
            <Col xs={24} md={8}>
              <Form.Item
                label="Rate Limit Up (kbps)"
                name="rate_limit_up"
              >
                <InputNumber
                  min={0}
                  max={1000000}
                  style={{ width: '100%' }}
                  placeholder="Optional"
                />
              </Form.Item>
            </Col>
            <Col xs={24} md={8}>
              <Form.Item
                label="Rate Limit Down (kbps)"
                name="rate_limit_down"
              >
                <InputNumber
                  min={0}
                  max={1000000}
                  style={{ width: '100%' }}
                  placeholder="Optional"
                />
              </Form.Item>
            </Col>
          </Row>
        </Card>

        <Divider />

        {/* Data Limits */}
        <Card title="Data Limits" className="config-card">
          <Row gutter={16}>
            <Col xs={24} md={12}>
              <Form.Item
                label="Daily Data Limit (MB)"
                name="daily_data_limit"
                tooltip="Total data allowed per user per day"
              >
                <InputNumber
                  min={0}
                  style={{ width: '100%' }}
                  placeholder="0 (unlimited)"
                  onChange={(value) => {
                    // Convert MB to bytes for storage
                    form.setFieldValue('daily_data_limit', value ? value * 1024 * 1024 : null);
                  }}
                />
              </Form.Item>
            </Col>
            <Col xs={24} md={12}>
              <Form.Item
                label="Session Data Limit (MB)"
                name="session_data_limit"
                tooltip="Data allowed per single session"
              >
                <InputNumber
                  min={0}
                  style={{ width: '100%' }}
                  placeholder="0 (unlimited)"
                  onChange={(value) => {
                    form.setFieldValue('session_data_limit', value ? value * 1024 * 1024 : null);
                  }}
                />
              </Form.Item>
            </Col>
          </Row>
        </Card>

        <Divider />

        {/* MAC Filtering */}
        <Card title="MAC Address Filtering" className="config-card">
          <Row gutter={16}>
            <Col span={24}>
              <Form.Item
                label="Enable MAC Filtering"
                name="enable_mac_filtering"
                valuePropName="checked"
              >
                <Switch />
              </Form.Item>
            </Col>
            <Col xs={24} md={12}>
              <Form.Item
                label="Allowed MAC Addresses"
                name="allowed_mac_addresses"
                tooltip="One MAC address per line (format: AA:BB:CC:DD:EE:FF)"
              >
                <Input.TextArea
                  rows={4}
                  placeholder="AA:BB:CC:DD:EE:FF&#10;11:22:33:44:55:66"
                />
              </Form.Item>
            </Col>
            <Col xs={24} md={12}>
              <Form.Item
                label="Blocked MAC Addresses"
                name="blocked_mac_addresses"
                tooltip="One MAC address per line"
              >
                <Input.TextArea
                  rows={4}
                  placeholder="AA:BB:CC:DD:EE:FF&#10;11:22:33:44:55:66"
                />
              </Form.Item>
            </Col>
          </Row>
        </Card>

        <Divider />

        {/* Advanced Settings */}
        <Card title="Advanced Settings" className="config-card">
          <Row gutter={16}>
            <Col xs={24} md={12}>
              <Form.Item
                label="Authentication Type"
                name="auth_type"
              >
                <Input disabled value="external" />
              </Form.Item>
            </Col>
            <Col xs={24} md={12}>
              <Form.Item
                label="Redirect URL"
                name="redirect_url"
                tooltip="URL to redirect after authentication"
              >
                <Input placeholder="http://success.page.com" />
              </Form.Item>
            </Col>
            <Col span={24}>
              <Form.Item
                label="Active Configuration"
                name="is_active"
                valuePropName="checked"
              >
                <Switch />
              </Form.Item>
            </Col>
          </Row>
        </Card>

        {/* Action Buttons */}
        <div className="form-actions">
          <Space>
            <Button icon={<ReloadOutlined />} onClick={handleReset}>
              Reset
            </Button>
            <Button
              type="primary"
              icon={<SaveOutlined />}
              onClick={handleSubmit}
              disabled={!hasChanges}
            >
              Save Configuration
            </Button>
          </Space>
        </div>
      </Form>
    </Spin>
  );
};

export default OmadaConfigForm;
