import React, { useState, useEffect } from 'react';
import { message, Button, Card, Form, Input, InputNumber, Switch, Space, Divider, Tag, Alert, Modal } from 'antd';
import { SaveOutlined, ReloadOutlined, EyeOutlined, HistoryOutlined } from '@ant-design/icons';
import api from '../services/api';
import './SMSSettings.css';

const { TextArea } = Input;

const SMSSettings = () => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [fetching, setFetching] = useState(true);
  const [settings, setSettings] = useState(null);
  const [preview, setPreview] = useState(null);
  const [showPreview, setShowPreview] = useState(false);

  useEffect(() => {
    fetchSettings();
  }, []);

  const fetchSettings = async () => {
    setFetching(true);
    try {
      const response = await api.get('/sms-settings/');
      setSettings(response.data);
      form.setFieldsValue(response.data);
    } catch (error) {
      message.error('Failed to load SMS settings');
      console.error(error);
    } finally {
      setFetching(false);
    }
  };

  const handleSave = async (values) => {
    setLoading(true);
    try {
      const response = await api.put('/sms-settings/', values);
      setSettings(response.data);
      message.success('SMS settings updated successfully!');
    } catch (error) {
      const errorMsg = error.response?.data?.detail || 'Failed to update settings';
      message.error(errorMsg);
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const handlePreview = async () => {
    const template = form.getFieldValue('otp_template');
    if (!template) {
      message.warning('Please enter a template first');
      return;
    }

    try {
      const response = await api.post('/sms-settings/preview', { template });
      setPreview(response.data);
      setShowPreview(true);
    } catch (error) {
      message.error('Failed to generate preview');
      console.error(error);
    }
  };

  const handleReset = () => {
    Modal.confirm({
      title: 'Reset to Default Settings?',
      content: 'This will restore the default OTP message template and settings. Are you sure?',
      okText: 'Yes, Reset',
      okType: 'danger',
      cancelText: 'Cancel',
      onOk: async () => {
        setLoading(true);
        try {
          const response = await api.post('/sms-settings/reset');
          setSettings(response.data);
          form.setFieldsValue(response.data);
          message.success('Settings reset to defaults');
        } catch (error) {
          message.error('Failed to reset settings');
        } finally {
          setLoading(false);
        }
      }
    });
  };

  return (
    <div className="sms-settings-page">
      <div className="page-header">
        <h1>📱 SMS Settings</h1>
        <p>Customize OTP message templates and SMS configuration (Superadmin Only)</p>
      </div>

      {/* Help Alert */}
      <Alert
        message="Available Template Placeholders"
        description={
          <div>
            <p style={{ marginBottom: 8 }}>You can use these placeholders in your OTP template:</p>
            <Space wrap>
              <Tag color="blue">{'{otp}'}</Tag>
              <span>The OTP code</span>
            </Space>
            <Space wrap style={{ marginLeft: 16 }}>
              <Tag color="green">{'{validity}'}</Tag>
              <span>Validity period in minutes</span>
            </Space>
            <Space wrap style={{ marginLeft: 16 }}>
              <Tag color="orange">{'{portal_url}'}</Tag>
              <span>Portal URL/domain</span>
            </Space>
            <Space wrap style={{ marginLeft: 16 }}>
              <Tag color="purple">{'{sender}'}</Tag>
              <span>Sender ID</span>
            </Space>
          </div>
        }
        type="info"
        showIcon
        style={{ marginBottom: 24 }}
      />

      <Card loading={fetching}>
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSave}
          initialValues={{
            enable_primary_sms: true,
            enable_secondary_sms: true
          }}
        >
          {/* OTP Template */}
          <Form.Item
            label="OTP Message Template"
            name="otp_template"
            rules={[
              { required: true, message: 'Please enter OTP template' },
              { min: 10, message: 'Template must be at least 10 characters' },
              { max: 500, message: 'Template must be less than 500 characters' },
              {
                validator: (_, value) => {
                  if (value && !value.includes('{otp}')) {
                    return Promise.reject('Template must contain {otp} placeholder');
                  }
                  return Promise.resolve();
                }
              }
            ]}
            extra="The SMS message that will be sent to users. Must include {otp} placeholder."
          >
            <TextArea
              rows={4}
              placeholder="Your NTC WiFi OTP: {otp}\nValid for {validity} minutes. Do not share.\n\n@{portal_url} #{otp}"
              maxLength={500}
              showCount
            />
          </Form.Item>

          <Button
            type="default"
            icon={<EyeOutlined />}
            onClick={handlePreview}
            style={{ marginBottom: 24 }}
          >
            Preview Message
          </Button>

          <Divider />

          {/* Settings Grid */}
          <div className="settings-grid">
            {/* Sender ID */}
            <Form.Item
              label="Sender ID"
              name="sender_id"
              rules={[
                { required: true, message: 'Please enter sender ID' },
                { min: 3, message: 'Sender ID must be at least 3 characters' },
                { max: 20, message: 'Sender ID must be less than 20 characters' },
                { pattern: /^[a-zA-Z0-9\s-]+$/, message: 'Sender ID must be alphanumeric' }
              ]}
              extra="The name that appears as the SMS sender"
            >
              <Input placeholder="NTC" maxLength={20} />
            </Form.Item>

            {/* OTP Validity */}
            <Form.Item
              label="OTP Validity (minutes)"
              name="otp_validity_minutes"
              rules={[
                { required: true, message: 'Please enter validity period' }
              ]}
              extra="How long the OTP remains valid"
            >
              <InputNumber min={1} max={60} style={{ width: '100%' }} />
            </Form.Item>

            {/* OTP Length */}
            <Form.Item
              label="OTP Code Length"
              name="otp_length"
              rules={[
                { required: true, message: 'Please enter OTP length' }
              ]}
              extra="Number of digits in OTP code"
            >
              <InputNumber min={4} max={8} style={{ width: '100%' }} />
            </Form.Item>

            {/* Max OTP per Hour */}
            <Form.Item
              label="Max OTP per Number (Hourly)"
              name="max_otp_per_number_per_hour"
              rules={[
                { required: true, message: 'Please enter hourly limit' }
              ]}
              extra="Prevent spam - limit OTPs per phone per hour"
            >
              <InputNumber min={1} max={20} style={{ width: '100%' }} />
            </Form.Item>

            {/* Max OTP per Day */}
            <Form.Item
              label="Max OTP per Number (Daily)"
              name="max_otp_per_number_per_day"
              rules={[
                { required: true, message: 'Please enter daily limit' }
              ]}
              extra="Maximum OTPs per phone per day"
            >
              <InputNumber min={1} max={50} style={{ width: '100%' }} />
            </Form.Item>
          </div>

          <Divider />

          {/* Enable/Disable Switches */}
          <div className="switches-section">
            <Form.Item
              label="Enable Primary SMS"
              name="enable_primary_sms"
              valuePropName="checked"
              extra="Main SMS provider (smsapp.pk)"
            >
              <Switch />
            </Form.Item>

            <Form.Item
              label="Enable Secondary SMS"
              name="enable_secondary_sms"
              valuePropName="checked"
              extra="Backup SMS provider (connect-afaq.ntc.org.pk)"
            >
              <Switch />
            </Form.Item>
          </div>

          {/* Action Buttons */}
          <div className="form-actions">
            <Space>
              <Button
                type="primary"
                icon={<SaveOutlined />}
                htmlType="submit"
                loading={loading}
                size="large"
              >
                Save Settings
              </Button>

              <Button
                icon={<ReloadOutlined />}
                onClick={fetchSettings}
                disabled={loading}
                size="large"
              >
                Reload
              </Button>

              <Button
                icon={<HistoryOutlined />}
                onClick={handleReset}
                disabled={loading}
                danger
                size="large"
              >
                Reset to Default
              </Button>
            </Space>
          </div>

          {/* Last Updated Info */}
          {settings && (
            <div className="last-updated">
              <small>
                Last updated: {new Date(settings.updated_at).toLocaleString()}
                {settings.updated_by && ` by ${settings.updated_by}`}
              </small>
            </div>
          )}
        </Form>
      </Card>

      {/* Preview Modal */}
      <Modal
        title="SMS Message Preview"
        open={showPreview}
        onCancel={() => setShowPreview(false)}
        footer={[
          <Button key="close" onClick={() => setShowPreview(false)}>
            Close
          </Button>
        ]}
        width={600}
      >
        {preview && (
          <div className="sms-preview">
            <Alert
              message="How it will look"
              description={
                <pre className="preview-message">{preview.formatted_message}</pre>
              }
              type="success"
              style={{ marginBottom: 16 }}
            />

            <div className="preview-stats">
              <Space direction="vertical" style={{ width: '100%' }}>
                <div className="stat-row">
                  <span>📏 Character Count:</span>
                  <strong>{preview.character_count} chars</strong>
                </div>
                <div className="stat-row">
                  <span>📱 SMS Parts:</span>
                  <strong>{preview.sms_parts} message(s)</strong>
                </div>
                <div className="stat-row">
                  <span>💰 Estimated Cost:</span>
                  <strong>{preview.estimated_cost}</strong>
                </div>
              </Space>
            </div>

            {preview.sms_parts > 1 && (
              <Alert
                message="Multi-part SMS"
                description={`This message will be sent as ${preview.sms_parts} separate SMS parts. Consider making it shorter to reduce costs.`}
                type="warning"
                style={{ marginTop: 16 }}
                showIcon
              />
            )}
          </div>
        )}
      </Modal>
    </div>
  );
};

export default SMSSettings;
