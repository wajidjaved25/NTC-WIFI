import { useState, useEffect } from 'react';
import {
  Modal,
  Form,
  Input,
  InputNumber,
  Select,
  Switch,
  Row,
  Col,
  Radio,
  Divider,
  Alert,
  Space
} from 'antd';

const { Option } = Select;

const SiteFormModal = ({
  visible,
  onClose,
  onSubmit,
  editingSite,
  form,
  omadaConfigs
}) => {
  const [useExistingConfig, setUseExistingConfig] = useState(true);
  const [selectedConfig, setSelectedConfig] = useState(null);

  useEffect(() => {
    if (visible) {
      // If editing, check if site has omada_config_id
      if (editingSite && editingSite.omada_config_id) {
        setUseExistingConfig(true);
        setSelectedConfig(editingSite.omada_config_id);
      } else if (editingSite) {
        setUseExistingConfig(false);
      } else {
        // New site - default to existing config if available
        if (omadaConfigs && omadaConfigs.length > 0) {
          setUseExistingConfig(true);
          setSelectedConfig(omadaConfigs[0].id);
          form.setFieldsValue({ 
            omada_config_id: omadaConfigs[0].id,
            omada_site_id: 'Default'
          });
        }
      }
    }
  }, [visible, editingSite, omadaConfigs, form]);

  const handleConfigChange = (value) => {
    setSelectedConfig(value);
    const config = omadaConfigs.find(c => c.id === value);
    if (config) {
      form.setFieldsValue({
        omada_site_id: config.site_id || 'Default'
      });
    }
  };

  const handleModeChange = (e) => {
    const useExisting = e.target.value;
    setUseExistingConfig(useExisting);
    
    if (useExisting) {
      // Clear custom fields
      form.setFieldsValue({
        omada_controller_ip: undefined,
        omada_controller_port: undefined,
        omada_username: undefined,
        omada_password: undefined
      });
      
      // Set config_id if available
      if (omadaConfigs && omadaConfigs.length > 0) {
        form.setFieldsValue({ omada_config_id: omadaConfigs[0].id });
        setSelectedConfig(omadaConfigs[0].id);
      }
    } else {
      // Clear config_id
      form.setFieldsValue({ omada_config_id: null });
      setSelectedConfig(null);
    }
  };

  return (
    <Modal
      title={editingSite ? 'Edit Site' : 'Add New Site'}
      open={visible}
      onOk={onSubmit}
      onCancel={onClose}
      width={800}
      okText={editingSite ? 'Update' : 'Create'}
    >
      <Form form={form} layout="vertical">
        {/* Basic Info */}
        <Row gutter={16}>
          <Col span={12}>
            <Form.Item
              name="site_name"
              label="Site Name"
              rules={[{ required: true, message: 'Please enter site name' }]}
            >
              <Input placeholder="Main Office" />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item
              name="site_code"
              label="Site Code"
              rules={[
                { required: true, message: 'Please enter site code' },
                { max: 20, message: 'Max 20 characters' },
              ]}
            >
              <Input placeholder="MAIN" />
            </Form.Item>
          </Col>
        </Row>

        <Form.Item name="location" label="Location">
          <Input placeholder="Islamabad, Pakistan" />
        </Form.Item>

        <Divider>Omada Controller Configuration</Divider>

        {/* Controller Mode Selection */}
        <Form.Item label="Controller Configuration Mode">
          <Radio.Group
            onChange={handleModeChange}
            value={useExistingConfig}
          >
            <Space direction="vertical">
              <Radio value={true}>
                📌 Use Existing Omada Config (Same controller for all sites)
              </Radio>
              <Radio value={false}>
                ⚙️ Custom Controller (Site has its own controller)
              </Radio>
            </Space>
          </Radio.Group>
        </Form.Item>

        {useExistingConfig ? (
          // OPTION 1: Select from existing omada_config
          <>
            <Alert
              message="Shared Controller Mode"
              description="Select your existing Omada controller. Perfect when one controller manages multiple sites."
              type="info"
              showIcon
              style={{ marginBottom: 16 }}
            />
            
            <Form.Item
              name="omada_config_id"
              label="Select Omada Configuration"
              rules={[{ required: useExistingConfig, message: 'Please select a configuration' }]}
            >
              <Select
                placeholder="Select Omada Config"
                onChange={handleConfigChange}
                showSearch
                optionFilterProp="children"
              >
                {omadaConfigs && omadaConfigs.map(config => (
                  <Option key={config.id} value={config.id}>
                    {config.config_name} ({config.controller_url})
                  </Option>
                ))}
              </Select>
            </Form.Item>

            <Form.Item
              name="omada_site_id"
              label="Omada Site ID"
              tooltip="The Site ID within the Omada controller (e.g., Default, Branch, Mall)"
            >
              <Input placeholder="Default" />
            </Form.Item>
          </>
        ) : (
          // OPTION 2: Enter custom controller details
          <>
            <Alert
              message="Custom Controller Mode"
              description="This site has its own dedicated Omada controller. Enter its details below."
              type="warning"
              showIcon
              style={{ marginBottom: 16 }}
            />

            <Row gutter={16}>
              <Col span={16}>
                <Form.Item
                  name="omada_controller_ip"
                  label="Controller IP Address"
                  rules={[{ required: !useExistingConfig, message: 'Please enter IP' }]}
                >
                  <Input placeholder="192.168.1.50" />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item
                  name="omada_controller_port"
                  label="Port"
                >
                  <InputNumber min={1} max={65535} style={{ width: '100%' }} placeholder="8043" />
                </Form.Item>
              </Col>
            </Row>

            <Row gutter={16}>
              <Col span={12}>
                <Form.Item
                  name="omada_site_id"
                  label="Omada Site ID"
                >
                  <Input placeholder="Default" />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item name="omada_username" label="Username">
                  <Input placeholder="admin" />
                </Form.Item>
              </Col>
            </Row>

            <Form.Item name="omada_password" label="Password">
              <Input.Password placeholder="Enter password" />
            </Form.Item>
          </>
        )}

        <Divider>RADIUS Configuration</Divider>

        <Row gutter={16}>
          <Col span={12}>
            <Form.Item
              name="radius_nas_ip"
              label="RADIUS NAS IP"
              rules={[{ required: true, message: 'Please enter NAS IP' }]}
              tooltip="Usually the AP or gateway IP at this site"
            >
              <Input placeholder="192.168.1.50" />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item
              name="radius_coa_port"
              label="CoA Port"
              rules={[{ required: true, message: 'Please enter CoA port' }]}
              tooltip="Must be unique per site (e.g., 3799, 3800, 3801)"
            >
              <InputNumber min={1024} max={65535} style={{ width: '100%' }} placeholder="3799" />
            </Form.Item>
          </Col>
        </Row>

        <Form.Item
          name="radius_secret"
          label="RADIUS Secret"
          rules={[{ required: true, message: 'Please enter RADIUS secret' }]}
        >
          <Input.Password placeholder="testing123" />
        </Form.Item>

        <Form.Item name="portal_url" label="Custom Portal URL (Optional)">
          <Input placeholder="https://wifi.example.com" />
        </Form.Item>

        <Form.Item name="is_active" label="Active" valuePropName="checked" initialValue={true}>
          <Switch />
        </Form.Item>
      </Form>
    </Modal>
  );
};

export default SiteFormModal;
