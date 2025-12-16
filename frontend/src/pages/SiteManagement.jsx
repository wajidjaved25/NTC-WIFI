import { useState, useEffect } from 'react';
import {
  Card,
  Table,
  Button,
  Space,
  Tag,
  Modal,
  Form,
  Input,
  InputNumber,
  Switch,
  message,
  Popconfirm,
  Tabs,
  Statistic,
  Row,
  Col,
  Tooltip,
  Badge
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  EyeOutlined,
  WifiOutlined,
  DisconnectOutlined,
  EnvironmentOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ReloadOutlined
} from '@ant-design/icons';
import { siteAPI } from '../services/api';
import './SiteManagement.css';

const { TabPane } = Tabs;

const SiteManagement = () => {
  const [sites, setSites] = useState([]);
  const [loading, setLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [editingSite, setEditingSite] = useState(null);
  const [viewSiteModal, setViewSiteModal] = useState(null);
  const [siteStats, setSiteStats] = useState(null);
  const [activeSessions, setActiveSessions] = useState([]);
  const [form] = Form.useForm();

  useEffect(() => {
    fetchSites();
  }, []);

  const fetchSites = async () => {
    setLoading(true);
    try {
      const response = await siteAPI.getSites();
      setSites(response.data.sites || []);
    } catch (error) {
      message.error('Failed to fetch sites: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  const handleAdd = () => {
    setEditingSite(null);
    form.resetFields();
    // Set default values for new site
    form.setFieldsValue({
      omada_controller_port: 8043,
      is_active: true,
    });
    setModalVisible(true);
  };

  const handleEdit = (site) => {
    setEditingSite(site);
    form.setFieldsValue(site);
    setModalVisible(true);
  };

  const handleViewSite = async (site) => {
    setViewSiteModal(site);
    try {
      // Fetch site stats
      const statsRes = await siteAPI.getSiteStats(site.id);
      setSiteStats(statsRes.data);

      // Fetch active sessions
      const sessionsRes = await siteAPI.getSiteActiveSessions(site.id);
      setActiveSessions(sessionsRes.data.sessions || []);
    } catch (error) {
      message.error('Failed to fetch site details: ' + error.message);
    }
  };

  const handleDelete = async (id) => {
    try {
      await siteAPI.deleteSite(id);
      message.success('Site deleted successfully');
      fetchSites();
    } catch (error) {
      message.error('Failed to delete site: ' + error.response?.data?.detail || error.message);
    }
  };

  const handleDisconnect = async (siteId, username) => {
    try {
      await siteAPI.disconnectUser(siteId, { username });
      message.success(`User ${username} disconnected successfully`);
      // Refresh active sessions
      const sessionsRes = await siteAPI.getSiteActiveSessions(siteId);
      setActiveSessions(sessionsRes.data.sessions || []);
    } catch (error) {
      message.error('Failed to disconnect user: ' + error.message);
    }
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      
      if (editingSite) {
        await siteAPI.updateSite(editingSite.id, values);
        message.success('Site updated successfully');
      } else {
        await siteAPI.createSite(values);
        message.success('Site created successfully');
      }
      
      setModalVisible(false);
      form.resetFields();
      fetchSites();
    } catch (error) {
      if (error.errorFields) {
        message.error('Please fill in all required fields');
      } else {
        message.error(error.response?.data?.detail || 'Operation failed');
      }
    }
  };

  const columns = [
    {
      title: 'Status',
      dataIndex: 'is_active',
      key: 'is_active',
      width: 80,
      render: (active) => (
        <Badge
          status={active ? 'success' : 'default'}
          text={active ? 'Active' : 'Inactive'}
        />
      ),
    },
    {
      title: 'Site Name',
      dataIndex: 'site_name',
      key: 'site_name',
      render: (text, record) => (
        <Space>
          <EnvironmentOutlined />
          <strong>{text}</strong>
          <Tag color="blue">{record.site_code}</Tag>
        </Space>
      ),
    },
    {
      title: 'Location',
      dataIndex: 'location',
      key: 'location',
      render: (text) => text || '-',
    },
    {
      title: 'Controller IP',
      dataIndex: 'omada_controller_ip',
      key: 'omada_controller_ip',
      render: (text, record) => (
        <Tooltip title={`Port: ${record.omada_controller_port}`}>
          <code>{text}</code>
        </Tooltip>
      ),
    },
    {
      title: 'RADIUS NAS IP',
      dataIndex: 'radius_nas_ip',
      key: 'radius_nas_ip',
      render: (text) => <code>{text}</code>,
    },
    {
      title: 'CoA Port',
      dataIndex: 'radius_coa_port',
      key: 'radius_coa_port',
      render: (text) => (
        <Tag color="purple">
          <WifiOutlined /> {text}
        </Tag>
      ),
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 200,
      render: (_, record) => (
        <Space size="small">
          <Tooltip title="View Details">
            <Button
              type="link"
              icon={<EyeOutlined />}
              onClick={() => handleViewSite(record)}
            />
          </Tooltip>
          <Tooltip title="Edit">
            <Button
              type="link"
              icon={<EditOutlined />}
              onClick={() => handleEdit(record)}
            />
          </Tooltip>
          <Popconfirm
            title="Are you sure you want to delete this site?"
            onConfirm={() => handleDelete(record.id)}
            okText="Yes"
            cancelText="No"
          >
            <Tooltip title="Delete">
              <Button
                type="link"
                danger
                icon={<DeleteOutlined />}
              />
            </Tooltip>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const sessionColumns = [
    {
      title: 'Username',
      dataIndex: 'username',
      key: 'username',
    },
    {
      title: 'MAC Address',
      dataIndex: 'mac_address',
      key: 'mac_address',
      render: (mac) => <code>{mac}</code>,
    },
    {
      title: 'IP Address',
      dataIndex: 'ip_address',
      key: 'ip_address',
      render: (ip) => <code>{ip}</code>,
    },
    {
      title: 'Duration',
      dataIndex: 'duration',
      key: 'duration',
      render: (seconds) => {
        const mins = Math.floor(seconds / 60);
        return `${mins} mins`;
      },
    },
    {
      title: 'Data Usage',
      dataIndex: 'total_bytes',
      key: 'total_bytes',
      render: (bytes) => {
        const mb = (bytes / 1048576).toFixed(2);
        return `${mb} MB`;
      },
    },
    {
      title: 'Action',
      key: 'action',
      render: (_, record) => (
        <Popconfirm
          title="Disconnect this user?"
          onConfirm={() => handleDisconnect(viewSiteModal.id, record.username)}
          okText="Yes"
          cancelText="No"
        >
          <Button
            type="link"
            danger
            icon={<DisconnectOutlined />}
            size="small"
          >
            Disconnect
          </Button>
        </Popconfirm>
      ),
    },
  ];

  return (
    <div className="site-management">
      <Card
        title={
          <Space>
            <EnvironmentOutlined />
            <span>Site Management</span>
          </Space>
        }
        extra={
          <Space>
            <Button
              icon={<ReloadOutlined />}
              onClick={fetchSites}
              loading={loading}
            >
              Refresh
            </Button>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={handleAdd}
            >
              Add Site
            </Button>
          </Space>
        }
      >
        <Table
          columns={columns}
          dataSource={sites}
          rowKey="id"
          loading={loading}
          pagination={{
            pageSize: 10,
            showTotal: (total) => `Total ${total} sites`,
          }}
        />
      </Card>

      {/* Add/Edit Modal */}
      <Modal
        title={editingSite ? 'Edit Site' : 'Add New Site'}
        open={modalVisible}
        onOk={handleSubmit}
        onCancel={() => {
          setModalVisible(false);
          form.resetFields();
        }}
        width={700}
        okText={editingSite ? 'Update' : 'Create'}
      >
        <Form
          form={form}
          layout="vertical"
          initialValues={{
            omada_controller_port: 8043,
            is_active: true,
          }}
        >
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

          <h4>Omada Controller Settings</h4>
          <Row gutter={16}>
            <Col span={16}>
              <Form.Item
                name="omada_controller_ip"
                label="Controller IP Address"
                rules={[{ required: true, message: 'Please enter IP' }]}
              >
                <Input placeholder="192.168.1.50" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="omada_controller_port" label="Port">
                <InputNumber min={1} max={65535} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="omada_site_id" label="Omada Site ID">
                <Input placeholder="Default" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="omada_username" label="Omada Username">
                <Input placeholder="admin" />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item name="omada_password" label="Omada Password">
            <Input.Password placeholder="Enter password (optional)" />
          </Form.Item>

          <h4>RADIUS Configuration</h4>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="radius_nas_ip"
                label="RADIUS NAS IP"
                rules={[{ required: true, message: 'Please enter NAS IP' }]}
                tooltip="Usually same as Omada Controller IP"
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
                <InputNumber min={1024} max={65535} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            name="radius_secret"
            label="RADIUS Secret"
            rules={[{ required: true, message: 'Please enter RADIUS secret' }]}
          >
            <Input.Password placeholder="Enter shared secret" />
          </Form.Item>

          <Form.Item name="portal_url" label="Custom Portal URL">
            <Input placeholder="https://wifi.example.com (optional)" />
          </Form.Item>

          <Form.Item name="is_active" label="Active" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Modal>

      {/* View Site Modal */}
      <Modal
        title={
          <Space>
            <EnvironmentOutlined />
            {viewSiteModal?.site_name}
            <Tag color={viewSiteModal?.is_active ? 'green' : 'default'}>
              {viewSiteModal?.is_active ? 'Active' : 'Inactive'}
            </Tag>
          </Space>
        }
        open={!!viewSiteModal}
        onCancel={() => {
          setViewSiteModal(null);
          setSiteStats(null);
          setActiveSessions([]);
        }}
        footer={null}
        width={900}
      >
        <Tabs defaultActiveKey="stats">
          <TabPane tab="Statistics" key="stats">
            {siteStats && (
              <>
                <Row gutter={16} style={{ marginBottom: 24 }}>
                  <Col span={6}>
                    <Card>
                      <Statistic
                        title="Total Users"
                        value={siteStats.total_users}
                        prefix={<CheckCircleOutlined />}
                      />
                    </Card>
                  </Col>
                  <Col span={6}>
                    <Card>
                      <Statistic
                        title="Active Sessions"
                        value={siteStats.active_sessions}
                        prefix={<WifiOutlined />}
                        valueStyle={{ color: '#3f8600' }}
                      />
                    </Card>
                  </Col>
                  <Col span={6}>
                    <Card>
                      <Statistic
                        title="Today's Sessions"
                        value={siteStats.today_sessions}
                        prefix={<CheckCircleOutlined />}
                      />
                    </Card>
                  </Col>
                  <Col span={6}>
                    <Card>
                      <Statistic
                        title="Today's Data"
                        value={siteStats.today_data_mb}
                        suffix="MB"
                      />
                    </Card>
                  </Col>
                </Row>

                <Card size="small">
                  <p><strong>Site Code:</strong> {viewSiteModal?.site_code}</p>
                  <p><strong>Location:</strong> {viewSiteModal?.location || 'N/A'}</p>
                  <p><strong>Controller:</strong> {viewSiteModal?.omada_controller_ip}:{viewSiteModal?.omada_controller_port}</p>
                  <p><strong>RADIUS NAS:</strong> {viewSiteModal?.radius_nas_ip}</p>
                  <p><strong>CoA Port:</strong> {viewSiteModal?.radius_coa_port}</p>
                </Card>
              </>
            )}
          </TabPane>

          <TabPane
            tab={
              <span>
                Active Sessions
                <Badge
                  count={activeSessions.length}
                  style={{ marginLeft: 8 }}
                />
              </span>
            }
            key="sessions"
          >
            <Table
              columns={sessionColumns}
              dataSource={activeSessions}
              rowKey="session_id"
              pagination={{ pageSize: 5 }}
              size="small"
            />
          </TabPane>
        </Tabs>
      </Modal>
    </div>
  );
};

export default SiteManagement;
