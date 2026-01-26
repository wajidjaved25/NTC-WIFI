import React, { useState, useEffect } from 'react';
import { 
  message, 
  Spin, 
  Table, 
  Button, 
  Modal, 
  Space, 
  Tag, 
  Tooltip, 
  Card,
  Row,
  Col,
  Statistic,
  Badge,
  Popconfirm,
  InputNumber
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  SyncOutlined,
  HeartOutlined,
  WarningOutlined,
  ReloadOutlined
} from '@ant-design/icons';
import OmadaConfigForm from '../components/OmadaConfig/OmadaConfigForm';
import api from '../services/api';

const OmadaSettings = () => {
  const [loading, setLoading] = useState(true);
  const [controllers, setControllers] = useState([]);
  const [controllerStatus, setControllerStatus] = useState(null);
  const [modalVisible, setModalVisible] = useState(false);
  const [editingController, setEditingController] = useState(null);
  const [priorityModalVisible, setPriorityModalVisible] = useState(false);
  const [selectedController, setSelectedController] = useState(null);
  const [newPriority, setNewPriority] = useState(1);

  useEffect(() => {
    fetchControllers();
    fetchControllerStatus();
    // Refresh status every 30 seconds
    const interval = setInterval(() => {
      fetchControllerStatus();
    }, 30000);
    return () => clearInterval(interval);
  }, []);

  const fetchControllers = async () => {
    setLoading(true);
    try {
      const response = await api.get('/omada/configs');
      setControllers(response.data);
    } catch (error) {
      console.error('Failed to fetch controllers:', error);
      message.error('Failed to load Omada controllers');
    } finally {
      setLoading(false);
    }
  };

  const fetchControllerStatus = async () => {
    try {
      const response = await api.get('/omada/controller-status');
      setControllerStatus(response.data);
    } catch (error) {
      console.error('Failed to fetch controller status:', error);
    }
  };

  const handleAdd = () => {
    setEditingController(null);
    setModalVisible(true);
  };

  const handleEdit = (controller) => {
    setEditingController(controller);
    setModalVisible(true);
  };

  const handleDelete = async (controllerId) => {
    try {
      await api.delete(`/omada/configs/${controllerId}`);
      message.success('Controller deleted successfully');
      fetchControllers();
      fetchControllerStatus();
    } catch (error) {
      console.error('Failed to delete controller:', error);
      message.error(error.response?.data?.detail || 'Failed to delete controller');
    }
  };

  const handleActivate = async (controllerId) => {
    try {
      await api.post(`/omada/configs/${controllerId}/activate`);
      message.success('Controller activated successfully');
      fetchControllers();
    } catch (error) {
      console.error('Failed to activate controller:', error);
      message.error('Failed to activate controller');
    }
  };

  const handleHealthCheck = async (controllerId) => {
    try {
      message.loading('Running health check...', 0);
      const response = await api.post(`/omada/configs/${controllerId}/health-check`);
      message.destroy();
      if (response.data.is_healthy) {
        message.success(`Controller is healthy!`);
      } else {
        message.error(`Controller is unhealthy (${response.data.failure_count} failures)`);
      }
      fetchControllers();
      fetchControllerStatus();
    } catch (error) {
      message.destroy();
      console.error('Failed to run health check:', error);
      message.error('Failed to run health check');
    }
  };

  const handleResetHealth = async (controllerId) => {
    try {
      await api.post(`/omada/configs/${controllerId}/reset-health`);
      message.success('Controller health status reset');
      fetchControllers();
      fetchControllerStatus();
    } catch (error) {
      console.error('Failed to reset health:', error);
      message.error('Failed to reset health status');
    }
  };

  const handlePriorityChange = (controller) => {
    setSelectedController(controller);
    setNewPriority(controller.priority);
    setPriorityModalVisible(true);
  };

  const handleUpdatePriority = async () => {
    try {
      await api.patch(`/omada/configs/${selectedController.id}/priority`, null, {
        params: { priority: newPriority }
      });
      message.success('Priority updated successfully');
      setPriorityModalVisible(false);
      fetchControllers();
    } catch (error) {
      console.error('Failed to update priority:', error);
      message.error('Failed to update priority');
    }
  };

  const handleSave = async (values) => {
    try {
      const dataToSend = { ...values };
      if (editingController?.id && (!dataToSend.password || dataToSend.password.trim() === '')) {
        delete dataToSend.password;
      }
      
      const endpoint = editingController?.id 
        ? `/omada/configs/${editingController.id}` 
        : '/omada/configs';
      const method = editingController?.id ? 'patch' : 'post';
      
      await api[method](endpoint, dataToSend);
      message.success('Controller saved successfully!');
      setModalVisible(false);
      fetchControllers();
      fetchControllerStatus();
    } catch (error) {
      console.error('Failed to save controller:', error);
      message.error('Failed to save controller: ' + (error.response?.data?.detail || 'Unknown error'));
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
      
      if (values.password && values.password.trim()) {
        testData.password = values.password;
      } else if (editingController?.id) {
        testData.use_stored_password = true;
        testData.config_id = editingController.id;
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

  const getPriorityLabel = (priority) => {
    if (priority === 1) return 'Primary';
    if (priority === 2) return 'Backup 1';
    if (priority === 3) return 'Backup 2';
    return `Backup ${priority - 1}`;
  };

  const columns = [
    {
      title: 'Priority',
      dataIndex: 'priority',
      key: 'priority',
      width: 120,
      render: (priority, record) => (
        <Space>
          <Tag color={priority === 1 ? 'blue' : 'default'}>
            {getPriorityLabel(priority)}
          </Tag>
          <Button 
            size="small" 
            type="link"
            onClick={() => handlePriorityChange(record)}
          >
            Change
          </Button>
        </Space>
      ),
      sorter: (a, b) => a.priority - b.priority,
    },
    {
      title: 'Name',
      dataIndex: 'config_name',
      key: 'config_name',
      render: (name, record) => (
        <Space>
          {name}
          {record.is_active && <Badge status="processing" text="Active" />}
        </Space>
      ),
    },
    {
      title: 'Controller URL',
      dataIndex: 'controller_url',
      key: 'controller_url',
    },
    {
      title: 'Site',
      dataIndex: 'site_id',
      key: 'site_id',
    },
    {
      title: 'Health Status',
      key: 'health',
      width: 150,
      render: (_, record) => {
        const status = controllerStatus?.controllers?.find(c => c.id === record.id);
        const isHealthy = record.is_healthy;
        const failureCount = record.failure_count || 0;
        
        return (
          <Space>
            {isHealthy ? (
              <Tooltip title="Controller is healthy">
                <CheckCircleOutlined style={{ color: '#52c41a', fontSize: 18 }} />
              </Tooltip>
            ) : (
              <Tooltip title={`Unhealthy - ${failureCount} consecutive failures`}>
                <CloseCircleOutlined style={{ color: '#ff4d4f', fontSize: 18 }} />
              </Tooltip>
            )}
            <span style={{ color: isHealthy ? '#52c41a' : '#ff4d4f' }}>
              {isHealthy ? 'Healthy' : 'Unhealthy'}
            </span>
          </Space>
        );
      },
    },
    {
      title: 'Last Check',
      dataIndex: 'last_health_check',
      key: 'last_health_check',
      width: 180,
      render: (lastCheck) => {
        if (!lastCheck) return 'Never';
        const date = new Date(lastCheck);
        const now = new Date();
        const diffMs = now - date;
        const diffMins = Math.floor(diffMs / 60000);
        
        if (diffMins < 1) return 'Just now';
        if (diffMins < 60) return `${diffMins}m ago`;
        const diffHours = Math.floor(diffMins / 60);
        if (diffHours < 24) return `${diffHours}h ago`;
        return date.toLocaleString();
      },
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 250,
      render: (_, record) => (
        <Space size="small">
          <Tooltip title="Edit controller">
            <Button
              size="small"
              icon={<EditOutlined />}
              onClick={() => handleEdit(record)}
            />
          </Tooltip>
          <Tooltip title="Run health check">
            <Button
              size="small"
              icon={<HeartOutlined />}
              onClick={() => handleHealthCheck(record.id)}
            />
          </Tooltip>
          {!record.is_healthy && (
            <Tooltip title="Reset health status">
              <Button
                size="small"
                icon={<ReloadOutlined />}
                onClick={() => handleResetHealth(record.id)}
              />
            </Tooltip>
          )}
          {!record.is_active && (
            <Tooltip title="Set as active">
              <Button
                size="small"
                type="primary"
                onClick={() => handleActivate(record.id)}
              >
                Activate
              </Button>
            </Tooltip>
          )}
          <Tooltip title="Delete controller">
            <Popconfirm
              title="Are you sure you want to delete this controller?"
              onConfirm={() => handleDelete(record.id)}
              okText="Yes"
              cancelText="No"
              disabled={record.is_active}
            >
              <Button
                size="small"
                danger
                icon={<DeleteOutlined />}
                disabled={record.is_active}
              />
            </Popconfirm>
          </Tooltip>
        </Space>
      ),
    },
  ];

  // Calculate statistics
  const totalControllers = controllers.length;
  const healthyControllers = controllers.filter(c => c.is_healthy).length;
  const primaryController = controllers.find(c => c.priority === 1);
  const activeController = controllers.find(c => c.is_active);

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '50px' }}>
        <Spin size="large" />
      </div>
    );
  }

  return (
    <div className="omada-settings">
      <div style={{ marginBottom: 24 }}>
        <h2>Omada Controller Management</h2>
        <p style={{ color: '#666', marginBottom: 16 }}>
          Manage multiple Omada controllers with automatic failover. The system will automatically
          switch to backup controllers if the primary fails.
        </p>

        {/* Statistics Cards */}
        <Row gutter={16} style={{ marginBottom: 24 }}>
          <Col xs={24} sm={12} lg={6}>
            <Card>
              <Statistic
                title="Total Controllers"
                value={totalControllers}
                prefix={<SyncOutlined />}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card>
              <Statistic
                title="Healthy Controllers"
                value={healthyControllers}
                valueStyle={{ color: healthyControllers === totalControllers ? '#3f8600' : '#cf1322' }}
                prefix={<CheckCircleOutlined />}
                suffix={`/ ${totalControllers}`}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card>
              <Statistic
                title="Primary Controller"
                value={primaryController?.config_name || 'None'}
                valueStyle={{ fontSize: 16 }}
              />
              {primaryController && (
                <Tag color={primaryController.is_healthy ? 'success' : 'error'} style={{ marginTop: 8 }}>
                  {primaryController.is_healthy ? 'Healthy' : 'Unhealthy'}
                </Tag>
              )}
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card>
              <Statistic
                title="Active Controller"
                value={activeController?.config_name || 'None'}
                valueStyle={{ fontSize: 16 }}
              />
              {activeController && (
                <Tag color="processing" style={{ marginTop: 8 }}>
                  Priority {activeController.priority}
                </Tag>
              )}
            </Card>
          </Col>
        </Row>

        {/* Warning if primary is unhealthy */}
        {primaryController && !primaryController.is_healthy && (
          <Card
            style={{ marginBottom: 16, borderColor: '#faad14' }}
            bodyStyle={{ padding: 16 }}
          >
            <Space>
              <WarningOutlined style={{ color: '#faad14', fontSize: 20 }} />
              <div>
                <strong>Primary Controller Unhealthy</strong>
                <p style={{ margin: 0, color: '#666' }}>
                  The primary controller is not responding. The system is using a backup controller
                  with priority {activeController?.priority || 'unknown'}.
                </p>
              </div>
            </Space>
          </Card>
        )}

        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={handleAdd}
          style={{ marginBottom: 16 }}
        >
          Add Controller
        </Button>
      </div>

      <Table
        columns={columns}
        dataSource={controllers}
        rowKey="id"
        loading={loading}
        pagination={false}
      />

      {/* Add/Edit Modal */}
      <Modal
        title={editingController ? 'Edit Controller' : 'Add Controller'}
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        footer={null}
        width={1000}
        destroyOnClose
      >
        <OmadaConfigForm
          initialData={editingController}
          onSave={handleSave}
          onTest={handleTest}
          loading={false}
        />
      </Modal>

      {/* Priority Change Modal */}
      <Modal
        title="Change Controller Priority"
        open={priorityModalVisible}
        onCancel={() => setPriorityModalVisible(false)}
        onOk={handleUpdatePriority}
        okText="Update"
      >
        <p>
          Set the priority for <strong>{selectedController?.config_name}</strong>.
          Lower numbers have higher priority (1 = Primary, 2 = Backup 1, etc.)
        </p>
        <Space>
          <span>Priority:</span>
          <InputNumber
            min={1}
            max={10}
            value={newPriority}
            onChange={setNewPriority}
          />
          <span>({getPriorityLabel(newPriority)})</span>
        </Space>
      </Modal>
    </div>
  );
};

export default OmadaSettings;
