import { useState, useEffect } from 'react';
import {
  Card,
  Table,
  Button,
  Space,
  Input,
  Modal,
  Form,
  Select,
  Tag,
  message,
  Popconfirm,
  Statistic,
  Row,
  Col,
  Descriptions,
  Pagination
} from 'antd';
import {
  UserOutlined,
  PlusOutlined,
  EditOutlined,
  LockOutlined,
  UnlockOutlined,
  DeleteOutlined,
  SearchOutlined,
  HistoryOutlined
} from '@ant-design/icons';
import api from '../services/api';
import dayjs from 'dayjs';

const { Option } = Select;

const UserManagement = () => {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [pagination, setPagination] = useState({
    current: 1,
    pageSize: 20,
    total: 0,
  });
  const [searchText, setSearchText] = useState('');
  const [filterBlocked, setFilterBlocked] = useState(null);
  const [createModalVisible, setCreateModalVisible] = useState(false);
  const [editModalVisible, setEditModalVisible] = useState(false);
  const [blockModalVisible, setBlockModalVisible] = useState(false);
  const [sessionsModalVisible, setSessionsModalVisible] = useState(false);
  const [selectedUser, setSelectedUser] = useState(null);
  const [userSessions, setUserSessions] = useState([]);
  const [blockReason, setBlockReason] = useState('');
  const [stats, setStats] = useState(null);
  const [form] = Form.useForm();
  const [editForm] = Form.useForm();

  useEffect(() => {
    fetchUsers();
    fetchStats();
  }, [pagination.current, pagination.pageSize, searchText, filterBlocked]);

  const fetchUsers = async () => {
    setLoading(true);
    try {
      const params = {
        page: pagination.current,
        page_size: pagination.pageSize,
        search: searchText || undefined,
        is_blocked: filterBlocked,
      };
      const response = await api.get('/user-management/users', { params });
      setUsers(response.data.users);
      setPagination({
        ...pagination,
        total: response.data.total,
      });
    } catch (error) {
      message.error('Failed to fetch users');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const fetchStats = async () => {
    try {
      const response = await api.get('/user-management/stats');
      setStats(response.data);
    } catch (error) {
      console.error('Failed to fetch stats:', error);
    }
  };

  const handleCreateUser = async (values) => {
    try {
      await api.post('/user-management/users', values);
      message.success('User created successfully');
      setCreateModalVisible(false);
      form.resetFields();
      fetchUsers();
      fetchStats();
    } catch (error) {
      message.error(error.response?.data?.detail || 'Failed to create user');
    }
  };

  const handleUpdateUser = async (values) => {
    try {
      await api.put(`/user-management/users/${selectedUser.id}`, values);
      message.success('User updated successfully');
      setEditModalVisible(false);
      editForm.resetFields();
      fetchUsers();
    } catch (error) {
      message.error(error.response?.data?.detail || 'Failed to update user');
    }
  };

  const handleBlockUser = async () => {
    if (!blockReason.trim()) {
      message.error('Please provide a reason for blocking');
      return;
    }
    try {
      await api.post(`/user-management/users/${selectedUser.id}/block`, null, {
        params: { reason: blockReason }
      });
      message.success('User blocked successfully');
      setBlockModalVisible(false);
      setBlockReason('');
      fetchUsers();
      fetchStats();
    } catch (error) {
      message.error(error.response?.data?.detail || 'Failed to block user');
    }
  };

  const handleUnblockUser = async (userId) => {
    try {
      await api.post(`/user-management/users/${userId}/unblock`);
      message.success('User unblocked successfully');
      fetchUsers();
      fetchStats();
    } catch (error) {
      message.error(error.response?.data?.detail || 'Failed to unblock user');
    }
  };

  const handleDeleteUser = async (userId) => {
    try {
      await api.delete(`/user-management/users/${userId}`);
      message.success('User deleted successfully');
      fetchUsers();
      fetchStats();
    } catch (error) {
      message.error(error.response?.data?.detail || 'Cannot delete user with sessions');
    }
  };

  const handleViewSessions = async (user) => {
    setSelectedUser(user);
    setSessionsModalVisible(true);
    try {
      const response = await api.get(`/user-management/users/${user.id}/sessions`);
      setUserSessions(response.data.sessions.items);
    } catch (error) {
      message.error('Failed to fetch user sessions');
    }
  };

  const openEditModal = (user) => {
    setSelectedUser(user);
    editForm.setFieldsValue({
      name: user.name,
      email: user.email,
      id_type: user.id_type,
      cnic: user.cnic,
      passport: user.passport,
    });
    setEditModalVisible(true);
  };

  const openBlockModal = (user) => {
    setSelectedUser(user);
    setBlockModalVisible(true);
  };

  const columns = [
    {
      title: 'Name',
      dataIndex: 'name',
      key: 'name',
      render: (text, record) => (
        <Space direction="vertical" size="small">
          <strong>{text}</strong>
          <small style={{ color: '#666' }}>{record.mobile}</small>
        </Space>
      ),
    },
    {
      title: 'ID',
      key: 'id',
      render: (_, record) => (
        <Space direction="vertical" size="small">
          {record.id_type && (
            <Tag color="blue">{record.id_type.toUpperCase()}</Tag>
          )}
          <small>{record.cnic || record.passport || 'N/A'}</small>
        </Space>
      ),
    },
    {
      title: 'Email',
      dataIndex: 'email',
      key: 'email',
      render: (text) => text || 'N/A',
    },
    {
      title: 'Status',
      key: 'status',
      render: (_, record) => (
        <Space direction="vertical" size="small">
          <Tag color={record.is_blocked ? 'red' : 'green'}>
            {record.is_blocked ? 'BLOCKED' : 'ACTIVE'}
          </Tag>
          {record.is_blocked && record.block_reason && (
            <small style={{ color: '#ff4d4f' }}>{record.block_reason}</small>
          )}
        </Space>
      ),
    },
    {
      title: 'Stats',
      key: 'stats',
      render: (_, record) => (
        <Space direction="vertical" size="small">
          <div>Sessions: {record.total_sessions}</div>
          <div>Data: {(record.total_data_usage / (1024 * 1024 * 1024)).toFixed(2)} GB</div>
        </Space>
      ),
    },
    {
      title: 'Created',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date) => dayjs(date).format('YYYY-MM-DD HH:mm'),
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_, record) => (
        <Space>
          <Button
            type="link"
            icon={<EditOutlined />}
            onClick={() => openEditModal(record)}
          >
            Edit
          </Button>
          {record.is_blocked ? (
            <Button
              type="link"
              icon={<UnlockOutlined />}
              onClick={() => handleUnblockUser(record.id)}
            >
              Unblock
            </Button>
          ) : (
            <Button
              type="link"
              danger
              icon={<LockOutlined />}
              onClick={() => openBlockModal(record)}
            >
              Block
            </Button>
          )}
          <Button
            type="link"
            icon={<HistoryOutlined />}
            onClick={() => handleViewSessions(record)}
          >
            Sessions
          </Button>
          <Popconfirm
            title="Delete this user?"
            description="Only users without sessions can be deleted."
            onConfirm={() => handleDeleteUser(record.id)}
            okText="Delete"
            cancelText="Cancel"
          >
            <Button type="link" danger icon={<DeleteOutlined />}>
              Delete
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const sessionColumns = [
    {
      title: 'Start Time',
      dataIndex: 'start_time',
      key: 'start_time',
      render: (date) => dayjs(date).format('YYYY-MM-DD HH:mm:ss'),
    },
    {
      title: 'End Time',
      dataIndex: 'end_time',
      key: 'end_time',
      render: (date) => date ? dayjs(date).format('YYYY-MM-DD HH:mm:ss') : 'Active',
    },
    {
      title: 'Duration',
      dataIndex: 'duration',
      key: 'duration',
      render: (seconds) => seconds ? `${Math.floor(seconds / 60)}m ${seconds % 60}s` : 'N/A',
    },
    {
      title: 'Data Usage',
      dataIndex: 'total_data',
      key: 'total_data',
      render: (bytes) => bytes ? `${(bytes / (1024 * 1024)).toFixed(2)} MB` : 'N/A',
    },
    {
      title: 'IP Address',
      dataIndex: 'ip_address',
      key: 'ip_address',
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (status) => (
        <Tag color={status === 'active' ? 'green' : 'default'}>
          {status?.toUpperCase()}
        </Tag>
      ),
    },
  ];

  return (
    <div style={{ padding: '24px' }}>
      <h2><UserOutlined /> WiFi User Management</h2>

      {/* Statistics */}
      {stats && (
        <Row gutter={16} style={{ marginBottom: 24 }}>
          <Col span={6}>
            <Card>
              <Statistic title="Total Users" value={stats.total_users} />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic 
                title="Active Users" 
                value={stats.active_users} 
                valueStyle={{ color: '#3f8600' }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic 
                title="Blocked Users" 
                value={stats.blocked_users}
                valueStyle={{ color: '#cf1322' }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic title="Users Today" value={stats.users_today} />
            </Card>
          </Col>
        </Row>
      )}

      {/* Filters */}
      <Card style={{ marginBottom: 16 }}>
        <Space>
          <Input
            placeholder="Search by name, mobile, CNIC, passport..."
            prefix={<SearchOutlined />}
            style={{ width: 300 }}
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            onPressEnter={fetchUsers}
          />
          <Select
            placeholder="Filter by status"
            style={{ width: 150 }}
            value={filterBlocked}
            onChange={setFilterBlocked}
            allowClear
          >
            <Option value={false}>Active Only</Option>
            <Option value={true}>Blocked Only</Option>
          </Select>
          <Button type="primary" onClick={fetchUsers}>
            Search
          </Button>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => setCreateModalVisible(true)}
          >
            Create User
          </Button>
        </Space>
      </Card>

      {/* Users Table */}
      <Card>
        <Table
          columns={columns}
          dataSource={users}
          rowKey="id"
          loading={loading}
          pagination={{
            ...pagination,
            showSizeChanger: true,
            showTotal: (total) => `Total ${total} users`,
          }}
          onChange={(newPagination) => setPagination(newPagination)}
        />
      </Card>

      {/* Create User Modal */}
      <Modal
        title="Create WiFi User"
        open={createModalVisible}
        onCancel={() => {
          setCreateModalVisible(false);
          form.resetFields();
        }}
        footer={null}
        width={600}
      >
        <Form form={form} layout="vertical" onFinish={handleCreateUser}>
          <Form.Item
            name="name"
            label="Full Name"
            rules={[{ required: true, message: 'Please enter name' }]}
          >
            <Input />
          </Form.Item>

          <Form.Item
            name="mobile"
            label="Mobile Number"
            rules={[{ required: true, message: 'Please enter mobile number' }]}
          >
            <Input placeholder="03001234567" />
          </Form.Item>

          <Form.Item name="email" label="Email">
            <Input type="email" />
          </Form.Item>

          <Form.Item name="id_type" label="ID Type">
            <Select placeholder="Select ID type">
              <Option value="cnic">CNIC</Option>
              <Option value="passport">Passport</Option>
            </Select>
          </Form.Item>

          <Form.Item
            noStyle
            shouldUpdate={(prevValues, currentValues) => 
              prevValues.id_type !== currentValues.id_type
            }
          >
            {({ getFieldValue }) =>
              getFieldValue('id_type') === 'cnic' ? (
                <Form.Item name="cnic" label="CNIC Number">
                  <Input placeholder="12345-1234567-1" />
                </Form.Item>
              ) : getFieldValue('id_type') === 'passport' ? (
                <Form.Item name="passport" label="Passport Number">
                  <Input placeholder="AB1234567" />
                </Form.Item>
              ) : null
            }
          </Form.Item>

          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">
                Create
              </Button>
              <Button onClick={() => {
                setCreateModalVisible(false);
                form.resetFields();
              }}>
                Cancel
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      {/* Edit User Modal */}
      <Modal
        title="Edit User"
        open={editModalVisible}
        onCancel={() => {
          setEditModalVisible(false);
          editForm.resetFields();
        }}
        footer={null}
        width={600}
      >
        <Form form={editForm} layout="vertical" onFinish={handleUpdateUser}>
          <Form.Item
            name="name"
            label="Full Name"
            rules={[{ required: true }]}
          >
            <Input />
          </Form.Item>

          <Form.Item name="email" label="Email">
            <Input type="email" />
          </Form.Item>

          <Form.Item name="id_type" label="ID Type">
            <Select>
              <Option value="cnic">CNIC</Option>
              <Option value="passport">Passport</Option>
            </Select>
          </Form.Item>

          <Form.Item name="cnic" label="CNIC Number">
            <Input placeholder="12345-1234567-1" />
          </Form.Item>

          <Form.Item name="passport" label="Passport Number">
            <Input placeholder="AB1234567" />
          </Form.Item>

          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">
                Update
              </Button>
              <Button onClick={() => {
                setEditModalVisible(false);
                editForm.resetFields();
              }}>
                Cancel
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      {/* Block User Modal */}
      <Modal
        title="Block User"
        open={blockModalVisible}
        onOk={handleBlockUser}
        onCancel={() => {
          setBlockModalVisible(false);
          setBlockReason('');
        }}
      >
        <p>Block user: <strong>{selectedUser?.name}</strong></p>
        <Input.TextArea
          placeholder="Enter reason for blocking..."
          value={blockReason}
          onChange={(e) => setBlockReason(e.target.value)}
          rows={4}
        />
      </Modal>

      {/* Sessions Modal */}
      <Modal
        title={`Session History - ${selectedUser?.name}`}
        open={sessionsModalVisible}
        onCancel={() => setSessionsModalVisible(false)}
        footer={null}
        width={1000}
      >
        <Table
          columns={sessionColumns}
          dataSource={userSessions}
          rowKey="id"
          pagination={{ pageSize: 10 }}
        />
      </Modal>
    </div>
  );
};

export default UserManagement;
