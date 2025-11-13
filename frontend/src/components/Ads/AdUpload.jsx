import React, { useState } from 'react';
import {
  Upload,
  Form,
  Input,
  InputNumber,
  Switch,
  DatePicker,
  Button,
  Card,
  Row,
  Col,
  message,
  Select,
  Space,
  Progress,
} from 'antd';
import { UploadOutlined, SaveOutlined, CloseOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';

const { TextArea } = Input;
const { RangePicker } = DatePicker;
const { Option } = Select;

const AdUpload = ({ onSave, onCancel, initialData, loading }) => {
  const [form] = Form.useForm();
  const [fileList, setFileList] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [adType, setAdType] = useState(initialData?.ad_type || 'image');

  const handleFileChange = ({ fileList: newFileList }) => {
    setFileList(newFileList);
  };

  const beforeUpload = (file) => {
    const isValidType = 
      (adType === 'video' && file.type.startsWith('video/')) ||
      (adType === 'image' && file.type.startsWith('image/')) ||
      (adType === 'download' && true); // Allow all for downloads

    if (!isValidType && adType !== 'download') {
      message.error(`Please upload a valid ${adType} file!`);
      return false;
    }

    const maxSize = adType === 'video' ? 100 : 10; // MB
    const isValidSize = file.size / 1024 / 1024 < maxSize;
    
    if (!isValidSize) {
      message.error(`File must be smaller than ${maxSize}MB!`);
      return false;
    }

    return false; // Prevent auto upload
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      
      if (fileList.length === 0 && !initialData) {
        message.error('Please upload a file!');
        return;
      }

      setUploading(true);
      
      const formData = new FormData();
      
      // Append form fields
      Object.keys(values).forEach(key => {
        if (values[key] !== undefined && values[key] !== null) {
          if (key === 'date_range' && values[key]) {
            formData.append('start_date', values[key][0].toISOString());
            formData.append('end_date', values[key][1].toISOString());
          } else if (typeof values[key] === 'boolean') {
            formData.append(key, values[key]);
          } else {
            formData.append(key, values[key]);
          }
        }
      });

      // Append file if exists
      if (fileList.length > 0) {
        formData.append('file', fileList[0].originFileObj);
      }

      // Simulate upload progress
      const interval = setInterval(() => {
        setUploadProgress(prev => {
          if (prev >= 90) {
            clearInterval(interval);
            return prev;
          }
          return prev + 10;
        });
      }, 200);

      await onSave(formData);
      
      clearInterval(interval);
      setUploadProgress(100);
      
      message.success('Advertisement saved successfully!');
      form.resetFields();
      setFileList([]);
      setUploadProgress(0);
      
    } catch (error) {
      message.error('Failed to save advertisement');
    } finally {
      setUploading(false);
    }
  };

  return (
    <Card title={initialData ? 'Edit Advertisement' : 'Upload New Advertisement'}>
      <Form
        form={form}
        layout="vertical"
        initialValues={{
          ad_type: 'image',
          display_duration: 10,
          display_order: 0,
          auto_skip: false,
          skip_after: 5,
          auto_disable: false,
          is_active: true,
          ...initialData,
        }}
      >
        <Row gutter={16}>
          <Col xs={24} md={12}>
            <Form.Item
              label="Advertisement Title"
              name="title"
              rules={[{ required: true, message: 'Please enter title' }]}
            >
              <Input placeholder="Enter ad title" />
            </Form.Item>
          </Col>

          <Col xs={24} md={12}>
            <Form.Item
              label="Advertisement Type"
              name="ad_type"
              rules={[{ required: true, message: 'Please select type' }]}
            >
              <Select onChange={setAdType}>
                <Option value="video">Video</Option>
                <Option value="image">Image</Option>
                <Option value="download">Download File</Option>
              </Select>
            </Form.Item>
          </Col>

          <Col span={24}>
            <Form.Item
              label="Description"
              name="description"
            >
              <TextArea rows={3} placeholder="Enter advertisement description" />
            </Form.Item>
          </Col>

          <Col span={24}>
            <Form.Item
              label={`Upload ${adType.charAt(0).toUpperCase() + adType.slice(1)}`}
              required={!initialData}
            >
              <Upload
                listType="picture-card"
                fileList={fileList}
                onChange={handleFileChange}
                beforeUpload={beforeUpload}
                maxCount={1}
                accept={
                  adType === 'video' ? 'video/*' :
                  adType === 'image' ? 'image/*' : '*'
                }
              >
                {fileList.length === 0 && (
                  <div>
                    <UploadOutlined />
                    <div style={{ marginTop: 8 }}>Upload</div>
                  </div>
                )}
              </Upload>
              <div style={{ marginTop: 8, color: '#999', fontSize: '12px' }}>
                {adType === 'video' && 'Max size: 100MB. Formats: MP4, AVI, MOV'}
                {adType === 'image' && 'Max size: 10MB. Formats: JPG, PNG, GIF'}
                {adType === 'download' && 'Max size: 50MB. Any file type'}
              </div>
            </Form.Item>
          </Col>

          {uploading && (
            <Col span={24}>
              <Progress percent={uploadProgress} status="active" />
            </Col>
          )}

          <Col xs={24} md={8}>
            <Form.Item
              label="Display Duration (seconds)"
              name="display_duration"
              rules={[{ required: true, message: 'Please enter duration' }]}
            >
              <InputNumber min={1} max={300} style={{ width: '100%' }} />
            </Form.Item>
          </Col>

          <Col xs={24} md={8}>
            <Form.Item
              label="Display Order"
              name="display_order"
              tooltip="Lower numbers display first"
            >
              <InputNumber min={0} max={100} style={{ width: '100%' }} />
            </Form.Item>
          </Col>

          <Col xs={24} md={8}>
            <Form.Item
              label="Skip After (seconds)"
              name="skip_after"
              tooltip="Time before skip button appears"
            >
              <InputNumber min={0} max={60} style={{ width: '100%' }} />
            </Form.Item>
          </Col>

          <Col span={24}>
            <Form.Item
              label="Schedule Date Range"
              name="date_range"
              tooltip="Leave empty for always active"
            >
              <RangePicker 
                showTime 
                style={{ width: '100%' }}
                format="YYYY-MM-DD HH:mm"
              />
            </Form.Item>
          </Col>

          <Col xs={24} md={8}>
            <Form.Item
              label="Allow Skip"
              name="auto_skip"
              valuePropName="checked"
            >
              <Switch />
            </Form.Item>
          </Col>

          <Col xs={24} md={8}>
            <Form.Item
              label="Auto Disable After End Date"
              name="auto_disable"
              valuePropName="checked"
            >
              <Switch />
            </Form.Item>
          </Col>

          <Col xs={24} md={8}>
            <Form.Item
              label="Active"
              name="is_active"
              valuePropName="checked"
            >
              <Switch />
            </Form.Item>
          </Col>
        </Row>

        <Row>
          <Col span={24} style={{ textAlign: 'right' }}>
            <Space>
              <Button icon={<CloseOutlined />} onClick={onCancel}>
                Cancel
              </Button>
              <Button
                type="primary"
                icon={<SaveOutlined />}
                onClick={handleSubmit}
                loading={uploading || loading}
              >
                Save Advertisement
              </Button>
            </Space>
          </Col>
        </Row>
      </Form>
    </Card>
  );
};

export default AdUpload;
