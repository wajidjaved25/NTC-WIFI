import React, { useState, useEffect } from 'react';
import { message, Spin } from 'antd';
import OmadaConfigForm from '../components/OmadaConfig/OmadaConfigForm';
import api from '../services/api';

const OmadaSettings = () => {
  const [loading, setLoading] = useState(true);
  const [config, setConfig] = useState(null);

  useEffect(() => {
    fetchConfig();
  }, []);

  const fetchConfig = async () => {
    setLoading(true);
    try {
      const response = await api.get('/omada/config');
      setConfig(response.data);
    } catch (error) {
      console.error('Failed to fetch config:', error);
      message.error('Failed to load Omada configuration');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async (values) => {
    try {
      // Remove empty password field if updating existing config
      const dataToSend = { ...values };
      if (config?.id && (!dataToSend.password || dataToSend.password.trim() === '')) {
        delete dataToSend.password;
      }
      
      // Use PATCH if updating existing config, POST if creating new
      const endpoint = config?.id ? `/omada/configs/${config.id}` : '/omada/configs';
      const method = config?.id ? 'patch' : 'post';
      const response = await api[method](endpoint, dataToSend);
      message.success('Configuration saved successfully!');
      setConfig(response.data);
      return response.data;
    } catch (error) {
      console.error('Failed to save config:', error);
      message.error('Failed to save configuration: ' + (error.response?.data?.detail || 'Unknown error'));
      throw error;
    }
  };

  const handleTest = async (values) => {
    try {
      const testData = {
        controller_url: values.controller_url,
        username: values.username,
        controller_id: values.controller_id,
        site_id: values.site_id,
      };
      
      // If password is provided, use it; otherwise use stored password
      if (values.password && values.password.trim()) {
        testData.password = values.password;
      } else if (config?.id) {
        // Use stored password for existing config
        testData.use_stored_password = true;
        testData.config_id = config.id;
      } else {
        throw new Error('Password is required for new configuration');
      }
      
      const response = await api.post('/omada/test-connection', testData);
      
      if (response.data.success) {
        message.success('Connection successful!');
      } else {
        throw new Error(response.data.message || 'Connection failed');
      }
    } catch (error) {
      console.error('Connection test failed:', error);
      message.error('Connection failed: ' + (error.response?.data?.detail || error.message));
      throw error;
    }
  };

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '50px' }}>
        <Spin size="large" />
      </div>
    );
  }

  return (
    <div className="omada-settings">
      <h2>Omada Controller Settings</h2>
      <p style={{ marginBottom: 24, color: '#666' }}>
        Configure your TP-Link Omada controller connection and session parameters.
      </p>
      
      <OmadaConfigForm
        initialData={config}
        onSave={handleSave}
        onTest={handleTest}
        loading={false}
      />
    </div>
  );
};

export default OmadaSettings;
