import React from 'react';
import { Card, Form, Row, Col, DatePicker, Input, Select, Button, Space } from 'antd';
import { SearchOutlined, ClearOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';

const { RangePicker } = DatePicker;
const { Option } = Select;

const RecordsFilters = ({ onFilter, onReset, loading }) => {
  const [form] = Form.useForm();

  const handleFinish = (values) => {
    const filters = {
      ...values,
      // Transform date_range to start_date and end_date for backend
      start_date: values.date_range ? values.date_range[0].format('YYYY-MM-DD') : null,
      end_date: values.date_range ? values.date_range[1].format('YYYY-MM-DD') : null,
    };
    
    // Remove date_range as backend doesn't expect it
    delete filters.date_range;
    
    onFilter(filters);
  };

  const handleReset = () => {
    form.resetFields();
    onReset();
  };

  return (
    <Card className="filters-card" style={{ marginBottom: 16 }}>
      <Form form={form} onFinish={handleFinish} layout="vertical">
        <Row gutter={16}>
          <Col xs={24} sm={12} md={8} lg={6}>
            <Form.Item label="Date Range" name="date_range">
              <RangePicker
                style={{ width: '100%' }}
                format="YYYY-MM-DD"
                placeholder={['Start Date', 'End Date']}
                presets={[
                  { label: 'Today', value: [dayjs(), dayjs()] },
                  { label: 'Yesterday', value: [dayjs().subtract(1, 'day'), dayjs().subtract(1, 'day')] },
                  { label: 'Last 7 Days', value: [dayjs().subtract(6, 'days'), dayjs()] },
                  { label: 'Last 30 Days', value: [dayjs().subtract(29, 'days'), dayjs()] },
                  { label: 'This Month', value: [dayjs().startOf('month'), dayjs()] },
                ]}
              />
            </Form.Item>
          </Col>

          <Col xs={24} sm={12} md={8} lg={6}>
            <Form.Item label="User Name" name="user_name">
              <Input placeholder="Search by name" allowClear />
            </Form.Item>
          </Col>

          <Col xs={24} sm={12} md={8} lg={6}>
            <Form.Item label="Mobile Number" name="mobile">
              <Input placeholder="Search by mobile" allowClear />
            </Form.Item>
          </Col>

          <Col xs={24} sm={12} md={8} lg={6}>
            <Form.Item label="CNIC" name="cnic">
              <Input placeholder="12345-1234567-1" allowClear />
            </Form.Item>
          </Col>

          <Col xs={24} sm={12} md={8} lg={6}>
            <Form.Item label="Passport Number" name="passport">
              <Input placeholder="AB1234567" allowClear />
            </Form.Item>
          </Col>

          <Col xs={24} sm={12} md={8} lg={6}>
            <Form.Item label="MAC Address" name="mac_address">
              <Input placeholder="AA:BB:CC:DD:EE:FF" allowClear />
            </Form.Item>
          </Col>

          <Col xs={24} sm={12} md={8} lg={6}>
            <Form.Item label="IP Address" name="ip_address">
              <Input placeholder="192.168.1.1" allowClear />
            </Form.Item>
          </Col>

          <Col xs={24} sm={12} md={8} lg={6}>
            <Form.Item label="Session Status" name="status">
              <Select placeholder="All Status" allowClear>
                <Option value="active">Active</Option>
                <Option value="completed">Completed</Option>
                <Option value="terminated">Terminated</Option>
              </Select>
            </Form.Item>
          </Col>

          <Col xs={24} sm={12} md={8} lg={6}>
            <Form.Item label="SSID" name="ssid">
              <Input placeholder="WiFi SSID" allowClear />
            </Form.Item>
          </Col>

          <Col xs={24} sm={12} md={8} lg={6}>
            <Form.Item label="Access Point" name="ap_name">
              <Input placeholder="AP Name" allowClear />
            </Form.Item>
          </Col>

          <Col xs={24} sm={12} md={8} lg={6}>
            <Form.Item label="Min Duration (minutes)" name="min_duration">
              <Input type="number" placeholder="0" min={0} />
            </Form.Item>
          </Col>

          <Col xs={24} sm={12} md={8} lg={6}>
            <Form.Item label="Max Duration (minutes)" name="max_duration">
              <Input type="number" placeholder="Unlimited" min={0} />
            </Form.Item>
          </Col>

          <Col xs={24} sm={12} md={8} lg={6}>
            <Form.Item label="Min Data Usage (MB)" name="min_data">
              <Input type="number" placeholder="0" min={0} />
            </Form.Item>
          </Col>

          <Col xs={24} sm={12} md={8} lg={6}>
            <Form.Item label="Max Data Usage (MB)" name="max_data">
              <Input type="number" placeholder="Unlimited" min={0} />
            </Form.Item>
          </Col>
        </Row>

        <Row>
          <Col span={24} style={{ textAlign: 'right' }}>
            <Space>
              <Button icon={<ClearOutlined />} onClick={handleReset}>
                Clear Filters
              </Button>
              <Button
                type="primary"
                htmlType="submit"
                icon={<SearchOutlined />}
                loading={loading}
              >
                Apply Filters
              </Button>
            </Space>
          </Col>
        </Row>
      </Form>
    </Card>
  );
};

export default RecordsFilters;
