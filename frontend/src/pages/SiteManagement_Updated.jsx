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
  Select,
  message,
  Popconfirm,
  Tabs,
  Tooltip,
  Badge,
  Row,
  Col,
  Statistic
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  EyeOutlined,
  EnvironmentOutlined,
  CloudServerOutlined,
  ReloadOutlined,
  WifiOutlined,
  DisconnectOutlined
} from '@ant-design/icons';
import { siteAPI } from '../services/api';
import './SiteManagement.css';

const { TabPane } = Tabs;
const { Option } = Select;

const SiteManagement = () => {
  const [controllers, setControllers] = useState([]);
  const [sites, setSites] = useState([]);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('sites');
  
  // Modals
  const [controllerModalVisible, setControllerModalVisible] = useState(false);
  const [siteModalVisible, setSiteModalVisible] = useState(false);
  const [editingController, setEditingController] = useState(null);
  const [editingSite, setEditingSite] = useState(null);
  const [viewSiteModal, setViewSiteModal] = useState(null);
  const [siteStats, setSiteStats] = useState(null);
  const [activeSessions, setActiveSessions] = useState([]);
  
  const [controllerForm] = Form.useForm();
  const [siteForm] = Form.useForm();

  useEffect(() => {
    fetchControllers();
    fetchSites();
  }, []);

  const fetchControllers = async () => {
    try {
      const response = await siteAPI.getControllers();
      setControllers(response.data || []);
    } catch (error) {
      message.error('Failed to fetch controllers: ' + error.message);
    }
  };

  const fetchSites = async () => {
    setLoading(true);
    try {
      const response = await siteAPI.getSites();
      setSites(response.data || []);
    } catch (error) {
      message.error('Failed to fetch sites: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  // ==================== CONTROLLER FUNCTIONS ====================

  const handleAddController = () => {
    setEditingController(null);
    controllerForm.resetFields();
    controllerForm.setFieldsValue({
      controller_type: 'cloud',
      controller_port: 8043,
      is_active: true
    });
    setControllerModalVisible(true);
  };

  const handleEditController = (controller) => {
    setEditingController(controller);
    controllerForm.setFieldsValue(controller);
    setControllerModalVisible(true);
  };

  const handleDeleteController = async (id) => {
    try {
      await siteAPI.deleteController(id);
      message.success('Controller deleted successfully');
      fetchControllers();
    } catch (error) {
      message.error(error.response?.data?.detail || 'Failed to delete controller');
    }
  };

  const handleControllerSubmit = async () => {
    try {
      const values = await controllerForm.validateFields();
      
      if (editingController) {
        await siteAPI.updateController(editingController.id, values);
        message.success('Controller updated successfully');
      } else {
        await siteAPI.createController(values);
        message.success('Controller created successfully');
      }
      
      setControllerModalVisible(false);
      controllerForm.resetFields();
      fetchControllers();
    } catch (error) {
      if (error.errorFields) {
        message.error('Please fill in all required fields');
      } else {
        message.error(error.response?.data?.detail || 'Operation failed');
      }
    }
  };

  // ==================== SITE FUNCTIONS ====================

  const handleAddSite = () => {
    if (controllers.length === 0) {
      message.warning('Please add an Omada controller first');
      setActiveTab('controllers');
      return;
    }
    setEditingSite(null);
    siteForm.resetFields();
    siteForm.setFieldsValue({
      omada_site_id: 'Default',
      is_active: true
    });
    setSiteModalVisible(true);
  };

  const handleEditSite = (site) => {
    setEditingSite(site);
    siteForm.setFieldsValue(site);
    setSiteModalVisible(true);
  };

  const handleDeleteSite = async (id) => {
    try {
      await siteAPI.deleteSite(id);
      message.success('Site deleted successfully');
      fetchSites();
    } catch (error) {
      message.error(error.response?.data?.detail || 'Failed to delete site');
    }
  };

  const handleSiteSubmit = async () => {
    try {
      const values = await siteForm.validateFields();
      
      if (editingSite) {
        await siteAPI.updateSite(editingSite.id, values);
        message.success('Site updated successfully');
      } else {
        await siteAPI.createSite(values);
        message.success('Site created successfully');
      }
      
      setSiteModalVisible(false);
      siteForm.resetFields();
      fetchSites();
    } catch (error) {
      if (error.errorFields) {
        message.error('Please fill in all required fields');
      } else {
        message.error(error.response?.data?.detail || 'Operation failed');
      }
    }
  };

  const handleViewSite = async (site) => {
    setViewSiteModal(site);
    try {
      const statsRes = await siteAPI.getSiteStats(site.id);
      setSiteStats(statsRes.data);

      const sessionsRes = await siteAPI.getSiteActiveSessions(site.id);
      setActiveSessions(sessionsRes.data.sessions || []);
    } catch (error) {
      message.error('Failed to fetch site details: ' + error.message);
    }
  };

  const handleDisconnect = async (siteId, username) => {
    try {
      await siteAPI.disconnectUser(siteId, { username });
      message.success(`User ${username} disconnected successfully`);
      const sessionsRes = await siteAPI.getSiteActiveSessions(siteId);
      setActiveSessions(sessionsRes.data.sessions || []);
    } catch (error) {
      message.error('Failed to disconnect user: ' + error.message);
    }
  };

  // ==================== TABLE COLUMNS ====================

  const controllerColumns = [
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
      title: 'Controller Name',
      dataIndex: 'controller_name',
      key: 'controller_name',
      render: (text, record) => (
        <Space>
          <CloudServerOutlined />
          <strong>{text}</strong>
          <Tag color={record.controller_type === 'cloud' ? 'blue' : 'green'}>
            {record.controller_type}
          </Tag>
        </Space>
      ),
    },
    {
      title: 'URL',
      dataIndex: 'controller_url',
      key: 'controller_url',
      render: (text) => <code>{text}</code>,
    },
    {
      title: 'Port',
      dataIndex: 'controller_port',
      key: 'controller_port',
    },
    {
      title: 'Sites',
      key: 'sites',
      render: (_, record) => {
        const siteCount = sites.filter(s => s.controller_id === record.id).length;
        return <Tag color="purple">{siteCount} sites</Tag>;
      },
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 150,
      render: (_, record) => (
        <Space size="small">
          <Tooltip title="Edit">
            <Button
              type="link"
              icon={<EditOutlined />}
              onClick={() => handleEditController(record)}
            />
          </Tooltip>
          <Popconfirm
            title="Delete this controller? All sites must be removed first."
            onConfirm={() => handleDeleteController(record.id)}
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

  const siteColumns = [
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
      title: 'Site',
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
      title: 'Controller',
      dataIndex: 'controller_name',
      key: 'controller_name',
      render: (text) => <Tag color="geekblue">{text}</Tag>,
    },
    {
      title: 'Omada Site ID',
      dataIndex: 'omada_site_id',
      key: 'omada_site_id',
      render: (text) => <code>{text}</code>,
    },
    {
      title: 'NAS IP',
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
              onClick={() => handleEditSite(record)}
            />
          </Tooltip>
          <Popconfirm
            title="Delete this site?"
            onConfirm={() => handleDeleteSite(record.id)}
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
      <Tabs activeKey={activeTab} onChange={setActiveTab}>
        {/* SITES TAB */}
        <TabPane
          tab={
            <span>
              <EnvironmentOutlined />
              Sites ({sites.length})
            </span>
          }
          key="sites"
        >
          <Card
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
                  onClick={handleAddSite}
                >
                  Add Site
                </Button>
              </Space>
            }
          >
            <Table
              columns={siteColumns}
              dataSource={sites}
              rowKey="id"
              loading={loading}
              pagination={{ pageSize: 10 }}
            />
          </Card>
        </TabPane>

        {/* CONTROLLERS TAB */}
        <TabPane
          tab={
            <span>
              <CloudServerOutlined />
              Controllers ({controllers.length})
            </span>
          }
          key="controllers"
        >
          <Card
            extra={
              <Space>
                <Button
                  icon={<ReloadOutlined />}
                  onClick={fetchControllers}
                >
                  Refresh
                </Button>
                <Button
                  type="primary"
                  icon={<PlusOutlined />}
                  onClick={handleAddController}
                >
                  Add Controller
                </Button>
              </Space>
            }
          >
            <Table
              columns={controllerColumns}
              dataSource={controllers}
              rowKey="id"
              pagination={{ pageSize: 10 }}
            />
          </Card>
        </TabPane>
      </Tabs>

      {/* CONTROLLER MODAL */}
      <Modal
        title={editingController ? 'Edit Controller' : 'Add Omada Controller'}
        open={controllerModalVisible}
        onOk={handleControllerSubmit}
        onCancel={() => {
          setControllerModalVisible(false);
          controllerForm.resetFields();
        }}
        width={600}
      >
        <Form form={controllerForm} layout="vertical">
          <Form.Item
            name="controller_name"
            label="Controller Name"
            rules={[{ required: true }]}
          >
            <Input placeholder="Main Omada Cloud" />
          </Form.Item>

          <Form.Item
            name="controller_type"
            label="Controller Type"
            rules={[{ required: true }]}
          >
            <Select>
              <Option value="cloud">Cloud Controller</Option>
              <Option value="on-premise">On-Premise Controller</Option>
            </Select>
          </Form.Item>

          <Row gutter={16}>
            <Col span={16}>
              <Form.Item
                name="controller_url"
                label="Controller URL"
                rules={[{ required: true }]}
              >
                <Input placeholder="https://omada.tplinkcloud.com" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="controller_port" label="Port">
                <InputNumber min={1} max={65535} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="username" label="Username">
                <Input placeholder="admin" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="password" label="Password">
                <Input.Password placeholder="Optional" />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item name="controller_id" label="Controller ID (for cloud)">
            <Input placeholder="Optional - for cloud controllers" />
          </Form.Item>

          <Form.Item name="is_active" label="Active" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Modal>

      {/* SITE MODAL */}
      <Modal
        title={editingSite ? 'Edit Site' : 'Add New Site'}
        open={siteModalVisible}
        onOk={handleSiteSubmit}
        onCancel={() => {
          setSiteModalVisible(false);
          siteForm.resetFields();
        }}
        width={700}
      >
        <Form form={siteForm} layout="vertical">
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="site_name"
                label="Site Name"
                rules={[{ required: true }]}
              >
                <Input placeholder="Main Office" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="site_code"
                label="Site Code"
                rules={[{ required: true, max: 20 }]}
              >
                <Input placeholder="MAIN" />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item name="location" label="Location">
            <Input placeholder="Islamabad, Pakistan" />
          </Form.Item>

          <Form.Item
            name="controller_id"
            label="Omada Controller"
            rules={[{ required: true }]}
            tooltip="Select which controller manages this site"
          >
            <Select placeholder="Select controller">
              {controllers.map(c => (
                <Option key={c.id} value={c.id}>
                  {c.controller_name} ({c.controller_type})
                </Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item
            name="omada_site_id"
            label="Omada Site ID"
            tooltip="The Site ID within Omada controller (e.g., Default, Branch, Mall)"
          >
            <Input placeholder="Default" />
          </Form.Item>

          <h4>RADIUS Configuration</h4>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="radius_nas_ip"
                label="RADIUS NAS IP"
                rules={[{ required: true }]}
              >
                <Input placeholder="192.168.1.50" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="radius_coa_port"
                label="CoA Port"
                rules={[{ required: true }]}
                tooltip="Must be unique per site!"
              >
                <InputNumber min={1024} max={65535} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            name="radius_secret"
            label="RADIUS Secret"
            rules={[{ required: true }]}
          >
            <Input.Password placeholder="testing123" />
          </Form.Item>

          <Form.Item name="portal_url" label="Custom Portal URL">
            <Input placeholder="Optional" />
          </Form.Item>

          <Form.Item name="is_active" label="Active" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Modal>

      {/* VIEW SITE MODAL - Same as before */}
      <Modal
        title={
          <Space>
            <EnvironmentOutlined />
            {viewSiteModal?.site_name}
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
        <Tabs>
          <TabPane tab="Statistics" key="stats">
            {siteStats && (
              <Row gutter={16}>
                <Col span={6}>
                  <Card>
                    <Statistic title="Total Users" value={siteStats.total_users} />
                  </Card>
                </Col>
                <Col span={6}>
                  <Card>
                    <Statistic title="Active Sessions" value={siteStats.active_sessions} />
                  </Card>
                </Col>
                <Col span={6}>
                  <Card>
                    <Statistic title="Today's Sessions" value={siteStats.today_sessions} />
                  </Card>
                </Col>
                <Col span={6}>
                  <Card>
                    <Statistic title="Today's Data" value={siteStats.today_data_mb} suffix="MB" />
                  </Card>
                </Col>
              </Row>
            )}
          </TabPane>
          <TabPane tab={`Active Sessions (${activeSessions.length})`} key="sessions">
            <Table
              columns={sessionColumns}
              dataSource={activeSessions}
              rowKey="session_id"
              size="small"
              pagination={{ pageSize: 5 }}
            />
          </TabPane>
        </Tabs>
      </Modal>
    </div>
  );
};

export default SiteManagement;
