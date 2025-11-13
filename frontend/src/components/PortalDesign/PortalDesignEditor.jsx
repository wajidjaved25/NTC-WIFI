import React, { useState, useEffect } from 'react';
import {
  Form,
  Input,
  Button,
  Card,
  Row,
  Col,
  Upload,
  Space,
  ColorPicker,
  Select,
  Switch,
  message,
  Divider,
} from 'antd';
import {
  UploadOutlined,
  SaveOutlined,
  EyeOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import ReactQuill from 'react-quill';
import 'react-quill/dist/quill.snow.css';
import './PortalDesignEditor.css';

const { TextArea } = Input;
const { Option } = Select;

const PortalDesignEditor = ({ initialData, onSave, onPreview, loading }) => {
  const [form] = Form.useForm();
  const [logoFile, setLogoFile] = useState([]);
  const [backgroundFile, setBackgroundFile] = useState([]);
  const [welcomeText, setWelcomeText] = useState('');
  const [termsText, setTermsText] = useState('');
  const [colors, setColors] = useState({
    primary_color: '#1890ff',
    secondary_color: '#ffffff',
    accent_color: '#52c41a',
    text_color: '#000000',
    background_color: '#f0f2f5',
  });

  useEffect(() => {
    if (initialData) {
      // Set all form values including show_logo and show_background
      const formValues = {
        ...initialData,
        show_logo: initialData.show_logo ?? true,  // Default to true if undefined
        show_background: initialData.show_background ?? false,  // Default to false if undefined
      };
      form.setFieldsValue(formValues);
      
      setWelcomeText(initialData.welcome_text || '');
      setTermsText(initialData.terms_text || '');
      setColors({
        primary_color: initialData.primary_color || '#1890ff',
        secondary_color: initialData.secondary_color || '#ffffff',
        accent_color: initialData.accent_color || '#52c41a',
        text_color: initialData.text_color || '#000000',
        background_color: initialData.background_color || '#f0f2f5',
      });
      
      console.log('Form initialized with values:', formValues);
    }
  }, [initialData, form]);

  const handleColorChange = (colorKey, color) => {
    const hexColor = typeof color === 'string' ? color : color.toHexString();
    setColors(prev => ({
      ...prev,
      [colorKey]: hexColor,
    }));
    form.setFieldValue(colorKey, hexColor);
  };

  const handleLogoUpload = ({ fileList }) => {
    setLogoFile(fileList);
  };

  const handleBackgroundUpload = ({ fileList }) => {
    setBackgroundFile(fileList);
  };

  const beforeUpload = (file) => {
    const isImage = file.type.startsWith('image/');
    if (!isImage) {
      message.error('You can only upload image files!');
      return false;
    }
    const isLt2M = file.size / 1024 / 1024 < 2;
    if (!isLt2M) {
      message.error('Image must be smaller than 2MB!');
      return false;
    }
    return false; // Prevent auto upload
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      
      console.log('Form values before submit:', values);
      
      const formData = new FormData();
      
      // Append form fields (including show_logo and show_background from Switch components)
      Object.keys(values).forEach(key => {
        if (values[key] !== undefined && values[key] !== null) {
          // Convert boolean values explicitly
          if (typeof values[key] === 'boolean') {
            const stringValue = values[key] ? 'true' : 'false';
            formData.append(key, stringValue);
            console.log(`${key}: ${values[key]} -> "${stringValue}"`);
          } else {
            formData.append(key, values[key]);
          }
        }
      });

      // Append colors
      Object.keys(colors).forEach(key => {
        formData.append(key, colors[key]);
      });

      // Append text content
      formData.append('welcome_text', welcomeText);
      formData.append('terms_text', termsText);

      // Append files
      if (logoFile.length > 0) {
        formData.append('logo', logoFile[0].originFileObj);
      }
      if (backgroundFile.length > 0) {
        formData.append('background', backgroundFile[0].originFileObj);
      }

      console.log('Submitting form data...');
      await onSave(formData);
      message.success('Portal design saved successfully!');
    } catch (error) {
      console.error('Submit error:', error);
      message.error('Failed to save portal design');
    }
  };

  const handlePreview = () => {
    const values = form.getFieldsValue();
    const previewData = {
      ...values,
      ...colors,
      welcome_text: welcomeText,
      terms_text: termsText,
    };
    onPreview(previewData);
  };

  const handleReset = () => {
    form.resetFields();
    setLogoFile([]);
    setBackgroundFile([]);
    setWelcomeText('');
    setTermsText('');
    setColors({
      primary_color: '#1890ff',
      secondary_color: '#ffffff',
      accent_color: '#52c41a',
      text_color: '#000000',
      background_color: '#f0f2f5',
    });
  };

  return (
    <div className="portal-design-editor">
      <Form form={form} layout="vertical">
        {/* Template Name */}
        <Card title="Template Information" style={{ marginBottom: 16 }}>
          <Row gutter={16}>
            <Col xs={24} md={12}>
              <Form.Item
                label="Template Name"
                name="template_name"
                rules={[{ required: true, message: 'Please enter template name' }]}
              >
                <Input placeholder="e.g., Summer Theme" />
              </Form.Item>
            </Col>
            <Col xs={24} md={12}>
              <Form.Item
                label="Layout Type"
                name="layout_type"
              >
                <Select>
                  <Option value="centered">Centered</Option>
                  <Option value="split">Split Screen</Option>
                  <Option value="fullscreen">Fullscreen</Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>
        </Card>

        {/* Branding */}
        <Card title="Branding" style={{ marginBottom: 16 }}>
          <Row gutter={16}>
            <Col xs={24} md={12}>
              <Form.Item label="Logo">
                <Upload
                  listType="picture-card"
                  fileList={logoFile}
                  onChange={handleLogoUpload}
                  beforeUpload={beforeUpload}
                  maxCount={1}
                  accept="image/*"
                >
                  {logoFile.length === 0 && (
                    <div>
                      <UploadOutlined />
                      <div style={{ marginTop: 8 }}>Upload Logo</div>
                    </div>
                  )}
                </Upload>
                <div style={{ color: '#999', fontSize: '12px' }}>
                  Recommended: 200x80px, PNG with transparency
                </div>
              </Form.Item>
              <Form.Item 
                label="Show Logo" 
                name="show_logo" 
                valuePropName="checked"
                tooltip="Enable/disable logo display on portal"
              >
                <Switch />
              </Form.Item>
            </Col>
            <Col xs={24} md={12}>
              <Form.Item label="Background Image">
                <Upload
                  listType="picture-card"
                  fileList={backgroundFile}
                  onChange={handleBackgroundUpload}
                  beforeUpload={beforeUpload}
                  maxCount={1}
                  accept="image/*"
                >
                  {backgroundFile.length === 0 && (
                    <div>
                      <UploadOutlined />
                      <div style={{ marginTop: 8 }}>Upload Background</div>
                    </div>
                  )}
                </Upload>
                <div style={{ color: '#999', fontSize: '12px' }}>
                  Recommended: 1920x1080px, JPG/PNG
                </div>
              </Form.Item>
              <Form.Item 
                label="Show Background" 
                name="show_background" 
                valuePropName="checked"
                tooltip="Enable/disable background image on portal"
              >
                <Switch />
              </Form.Item>
            </Col>
          </Row>
        </Card>

        {/* Color Scheme */}
        <Card title="Color Scheme" style={{ marginBottom: 16 }}>
          <Row gutter={[16, 16]}>
            <Col xs={24} sm={12} md={8} lg={4}>
              <Form.Item label="Primary Color" name="primary_color">
                <ColorPicker
                  value={colors.primary_color}
                  onChange={(color) => handleColorChange('primary_color', color)}
                  showText
                  format="hex"
                  size="small"
                  presets={[
                    {
                      label: 'Common',
                      colors: ['#1890ff', '#52c41a', '#faad14', '#f5222d', '#722ed1', '#13c2c2'],
                    },
                  ]}
                  panelRender={(panel) => (
                    <div style={{ maxWidth: '260px' }}>{panel}</div>
                  )}
                />
              </Form.Item>
            </Col>
            <Col xs={24} sm={12} md={8} lg={4}>
              <Form.Item label="Secondary Color" name="secondary_color">
                <ColorPicker
                  value={colors.secondary_color}
                  onChange={(color) => handleColorChange('secondary_color', color)}
                  showText
                  format="hex"
                  size="small"
                  presets={[
                    {
                      label: 'Common',
                      colors: ['#6a0ec7', '#722ed1', '#1890ff', '#13c2c2', '#52c41a', '#faad14'],
                    },
                  ]}
                  panelRender={(panel) => (
                    <div style={{ maxWidth: '260px' }}>{panel}</div>
                  )}
                />
              </Form.Item>
            </Col>
            <Col xs={24} sm={12} md={8} lg={4}>
              <Form.Item label="Accent Color" name="accent_color">
                <ColorPicker
                  value={colors.accent_color}
                  onChange={(color) => handleColorChange('accent_color', color)}
                  showText
                  format="hex"
                  size="small"
                  presets={[
                    {
                      label: 'Common',
                      colors: ['#52c41a', '#13c2c2', '#1890ff', '#faad14', '#f5222d', '#722ed1'],
                    },
                  ]}
                  panelRender={(panel) => (
                    <div style={{ maxWidth: '260px' }}>{panel}</div>
                  )}
                />
              </Form.Item>
            </Col>
            <Col xs={24} sm={12} md={8} lg={4}>
              <Form.Item label="Text Color" name="text_color">
                <ColorPicker
                  value={colors.text_color}
                  onChange={(color) => handleColorChange('text_color', color)}
                  showText
                  format="hex"
                  size="small"
                  presets={[
                    {
                      label: 'Common',
                      colors: ['#000000', '#262626', '#595959', '#8c8c8c', '#bfbfbf', '#ffffff'],
                    },
                  ]}
                  panelRender={(panel) => (
                    <div style={{ maxWidth: '260px' }}>{panel}</div>
                  )}
                />
              </Form.Item>
            </Col>
            <Col xs={24} sm={12} md={8} lg={4}>
              <Form.Item label="Background" name="background_color">
                <ColorPicker
                  value={colors.background_color}
                  onChange={(color) => handleColorChange('background_color', color)}
                  showText
                  format="hex"
                  size="small"
                  presets={[
                    {
                      label: 'Common',
                      colors: ['#ffffff', '#f5f5f5', '#e8e8e8', '#d9d9d9', '#bfbfbf', '#8c8c8c'],
                    },
                  ]}
                  panelRender={(panel) => (
                    <div style={{ maxWidth: '260px' }}>{panel}</div>
                  )}
                />
              </Form.Item>
            </Col>
          </Row>
        </Card>

        {/* Content */}
        <Card title="Portal Content" style={{ marginBottom: 16 }}>
          <Form.Item
            label="Welcome Title"
            name="welcome_title"
            rules={[{ required: true, message: 'Please enter welcome title' }]}
          >
            <Input placeholder="Welcome to Free WiFi" />
          </Form.Item>

          <Form.Item label="Welcome Message">
            <ReactQuill
              value={welcomeText}
              onChange={setWelcomeText}
              theme="snow"
              placeholder="Enter welcome message..."
              modules={{
                toolbar: [
                  ['bold', 'italic', 'underline'],
                  [{ list: 'ordered' }, { list: 'bullet' }],
                  ['link'],
                  ['clean'],
                ],
              }}
            />
          </Form.Item>

          <Divider />

          <Form.Item label="Terms & Conditions">
            <ReactQuill
              value={termsText}
              onChange={setTermsText}
              theme="snow"
              placeholder="Enter terms and conditions..."
              modules={{
                toolbar: [
                  ['bold', 'italic', 'underline'],
                  [{ list: 'ordered' }, { list: 'bullet' }],
                  ['link'],
                  ['clean'],
                ],
              }}
            />
          </Form.Item>

          <Form.Item
            label="Terms Checkbox Text"
            name="terms_checkbox_text"
            tooltip="Text shown next to the checkbox that users must accept"
            rules={[{ required: true, message: 'Please enter checkbox text' }]}
          >
            <Input placeholder="I accept the terms and conditions" />
          </Form.Item>

          <Divider />

          <Form.Item
            label="Footer Text"
            name="footer_text"
          >
            <Input placeholder="© 2025 Your Company. All rights reserved." />
          </Form.Item>
        </Card>

        {/* Custom CSS/JS */}
        <Card title="Advanced Customization" style={{ marginBottom: 16 }}>
          <Form.Item
            label="Custom CSS"
            name="custom_css"
            tooltip="Add custom CSS to further customize the portal"
          >
            <TextArea
              rows={6}
              placeholder="/* Add your custom CSS here */"
              style={{ fontFamily: 'monospace' }}
            />
          </Form.Item>

          <Form.Item
            label="Custom JavaScript"
            name="custom_js"
            tooltip="Add custom JavaScript (use with caution)"
          >
            <TextArea
              rows={6}
              placeholder="// Add your custom JavaScript here"
              style={{ fontFamily: 'monospace' }}
            />
          </Form.Item>
        </Card>

        {/* Actions */}
        <Card>
          <Space style={{ width: '100%', justifyContent: 'flex-end' }}>
            <Button icon={<ReloadOutlined />} onClick={handleReset}>
              Reset
            </Button>
            <Button
              icon={<EyeOutlined />}
              onClick={handlePreview}
            >
              Preview
            </Button>
            <Button
              type="primary"
              icon={<SaveOutlined />}
              onClick={handleSubmit}
              loading={loading}
            >
              Save Design
            </Button>
          </Space>
        </Card>
      </Form>
    </div>
  );
};

export default PortalDesignEditor;
