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
  Switch,
  Descriptions,
  Alert
} from 'antd';
import {
  TeamOutlined,
  PlusOutlined,
  EditOutlined,
  LockOutlined,
  UnlockOutlined,
  DeleteOutlined,
  SearchOutlined,
  KeyOutlined,
  CheckCircleOutlined,
  StopOutlined
} from '@ant-design/icons';
import api from '../services/api';
import dayjs from 'dayjs';

const { Option } = Select;

const AdminManagement = () => {
  const [admins, setAdmins] = useState([]);
  const [loading, setLoading] = useState(false);
  const [pagination, setPagination] = useState({
    current: 1,
    pageSize: 20,
    total: 0,
  });
  const [searchText, setSearchText] = useState('');
  const [filterRole, setFilterRole] = useState(null);
  const [filterActive, setFilterActive] = useState(null);
  const [createModalVisible, setCreateModalVisible] = useState(false);
  const [editModalVisible, setEditModalVisible] = useState(false);
  const [passwordModalVisible, setPasswordModalVisible] = useState(false);
  const [selectedAdmin, setSelectedAdmin] = useState(null);
  const [roles, setRoles] = useState([]);
  const [form] = Form.useForm();
  const [editForm] = Form.useForm();
  const [passwordForm] = Form.useForm();

  useEffect(() => {
    fetchAdmins();
    fetchRoles();
  }, [pagination.current, pagination.pageSize, searchText, filterRole, filterActive]);

  const fetchAdmins = async () => {
    setLoading(true);
    try {
      const params = {
        page: pagination.current,
        page_size: pagination.pageSize,
        search: searchText || undefined,
        role: filterRole,
        is_active: filterActive,
      };
      const response = await api.get('/admin-management/admins', { params });
      setAdmins(response.data.admins);
      setPagination({
        ...pagination,
        total: response.data.total,
      });
    } catch (error) {
      message.error('Failed to fetch admins');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const fetchRoles = async () => {
    try {
      const response = await api.get('/admin-management/roles');
      setRoles(response.data.roles);
    } catch (error) {
      console.error('Failed to fetch roles:', error);
    }
  };

  const handleCreateAdmin = async (values) => {
    try {
      await api.post('/admin-management/admins', values);
      message.success('Admin created successfully');
      setCreateModalVisible(false);
      form.resetFields();
      fetchAdmins();
    } catch (error) {
      message.error(error.response?.data?.detail || 'Failed to create admin');
    }
  };

  const handleUpdateAdmin = async (values) => {
    try {
      await api.put(`/admin-management/admins/${selectedAdmin.id}`, values);
      message.success('Admin updated successfully');
      setEditModalVisible(false);
      editForm.resetFields();
      fetchAdmins();
    } catch (error) {
      message.error(error.response?.data?.detail || 'Failed to update admin');
    }
  };

  const handleUpdatePassword = async (values) => {
    try {
      await api.put(`/admin-management/admins/${selectedAdmin.id}/password`, {
        new_password: values.new_password
      });
      message.success('Password updated successfully');
      setPasswordModalVisible(false);
      passwordForm.resetFields();
    } catch (error) {
      message.error(error.response?.data?.detail || 'Failed to update password');
    }
  };

  const handleActivateAdmin = async (adminId) => {
    try {
      await api.post(`/admin-management/admins/${adminId}/activate`);
      message.success('Admin activated successfully');
      fetchAdmins();
    } catch (error) {
      message.error(error.response?.data?.detail || 'Failed to activate admin');
    }
  };

  const handleDeactivateAdmin = async (adminId) => {
    try {
      await api.post(`/admin-management/admins/${adminId}/deactivate`);
      message.success('Admin deactivated successfully');
      fetchAdmins();
    } catch (error) {
      message.error(error.response?.data?.detail || 'Failed to deactivate admin');
    }
  };

  const handleDeleteAdmin = async (adminId) => {
    try {
      await api.delete(`/admin-management/admins/${adminId}`);
      message.success('Admin deleted successfully');
      fetchAdmins();
    } catch (error) {
      message.error(error.response?.data?.detail || 'Cannot delete admin');
    }
  };

  const openEditModal = (admin) => {
    setSelectedAdmin(admin);
    editForm.setFieldsValue({
      email: admin.email,
      full_name: admin.full_name,
      can_manage_portal: admin.can_manage_portal,
      can_manage_sessions: admin.can_manage_sessions,
      can_view_records: admin.can_view_records,
      can_view_ipdr: admin.can_view_ipdr,
      can_manage_radius: admin.can_manage_radius,
    });
    setEditModalVisible(true);
  };

  const openPasswordModal = (admin) => {
    setSelectedAdmin(admin);
    setPasswordModalVisible(true);
  };

  const getRoleTag = (role) => {
    const colors = {
      superadmin: 'red',
      admin: 'blue',
      ipdr_viewer: 'green',
    };
    return <Tag color={colors[role]}>{role.toUpperCase()}</Tag>;
  };

  const columns = [
    {
      title: 'Username',
      dataIndex: 'username',
      key: 'username',
      render: (text, record) => (
        <Space direction="vertical" size="small">
          <strong>{text}</strong>
          <small style={{ color: '#666' }}>{record.email}</small>
        </Space>
      ),
    },
    {
      title: 'Full Name',
      dataIndex: 'full_name',
      key: 'full_name',
    },
    {
      title: 'Role',
      dataIndex: 'role',
      key: 'role',
      render: (role) => getRoleTag(role),
    },
    {
      title: 'Status',
      dataIndex: 'is_active',
      key: 'is_active',
      render: (isActive) => (
        <Tag color={isActive ? 'green' : 'red'}>
          {isActive ? 'ACTIVE' : 'INACTIVE'}
        </Tag>
      ),
    },
    {
      title: 'Permissions',
      key: 'permissions',
      render: (_, record) => (
        <Space size="small" wrap>
          {record.can_manage_portal && <Tag color="blue">Portal</Tag>}
          {record.can_manage_sessions && <Tag color="cyan">Sessions</Tag>}
          {record.can_view_records && <Tag color="green">Records</Tag>}
          {record.can_view_ipdr && <Tag color="orange">IPDR</Tag>}
          {record.can_manage_radius && <Tag color="purple">RADIUS</Tag>}
        </Space>
      ),
    },
    {
      title: 'Last Login',
      dataIndex: 'last_login',
      key: 'last_login',
      render: (date) => date ? dayjs(date).format('YYYY-MM-DD HH:mm') : 'Never',
    },
    {
      title: 'Created',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date) => dayjs(date).format('YYYY-MM-DD'),
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_, record) => {
        if (record.role === 'superadmin') {
          return <Tag color="red">Protected</Tag>;
        }
        return (
          <Space>
            <Button
              type="link"
              icon={<EditOutlined />}
              onClick={() => openEditModal(record)}
            >
              Edit
            </Button>
            <Button
              type="link"
              icon={<KeyOutlined />}
              onClick={() => openPasswordModal(record)}
            >
              Password
            </Button>
            {record.is_active ? (
              <Button
                type="link"
                danger
                icon={<StopOutlined />}
                onClick={() => handleDeactivateAdmin(record.id)}
              >
                Deactivate
              </Button>
            ) : (
              <Button
                type="link"
                icon={<CheckCircleOutlined />}
                onClick={() => handleActivateAdmin(record.id)}
              >
                Activate
              </Button>
            )}
            <Popconfirm
              title="Delete this admin?"
              description="This action cannot be undone."
              onConfirm={() => handleDeleteAdmin(record.id)}
              okText="Delete"
              cancelText="Cancel"
            >
              <Button type="link" danger icon={<DeleteOutlined />}>
                Delete
              </Button>
            </Popconfirm>
          </Space>
        );
      },
    },
  ];

  return (
    <div style={{ padding: '24px' }}>
      <h2><TeamOutlined /> Admin User Management</h2>

      <Alert
        message="Superadmin Access Only"
        description="Only superadmin accounts can manage admin users. Superadmin accounts cannot be modified or deleted."
        type="warning"
        showIcon
        style={{ marginBottom: 16 }}
      />

      {/* Filters */}
      <Card style={{ marginBottom: 16 }}>
        <Space>
          <Input
            placeholder="Search by username, email, name..."
            prefix={<SearchOutlined />}
            style={{ width: 300 }}
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            onPressEnter={fetchAdmins}
          />
          <Select
            placeholder="Filter by role"
            style={{ width: 150 }}
            value={filterRole}
            onChange={setFilterRole}
            allowClear
          >
            <Option value="admin">Admin</Option>
            <Option value="ipdr_viewer">IPDR Viewer</Option>
            <Option value="superadmin">Superadmin</Option>
          </Select>
          <Select
            placeholder="Filter by status"
            style={{ width: 150 }}
            value={filterActive}
            onChange={setFilterActive}
            allowClear
          >
            <Option value={true}>Active Only</Option>
            <Option value={false}>Inactive Only</Option>
          </Select>
          <Button type="primary" onClick={fetchAdmins}>
            Search
          </Button>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => setCreateModalVisible(true)}
          >
            Create Admin
          </Button>
        </Space>
      </Card>

      {/* Admins Table */}
      <Card>
        <Table
          columns={columns}
          dataSource={admins}
          rowKey="id"
          loading={loading}
          pagination={{
            ...pagination,
            showSizeChanger: true,
            showTotal: (total) => `Total ${total} admins`,
          }}
          onChange={(newPagination) => setPagination(newPagination)}
        />
      </Card>

      {/* Create Admin Modal */}
      <Modal
        title="Create Admin User"
        open={createModalVisible}
        onCancel={() => {
          setCreateModalVisible(false);
          form.resetFields();
        }}
        footer={null}
        width={700}
      >
        <Form form={form} layout="vertical" onFinish={handleCreateAdmin}>
          <Form.Item
            name="username"
            label="Username"
            rules={[{ required: true, message: 'Please enter username' }]}
          >
            <Input />
          </Form.Item>

          <Form.Item
            name="email"
            label="Email"
            rules={[
              { required: true, message: 'Please enter email' },
              { type: 'email', message: 'Invalid email' }
            ]}
          >
            <Input />
          </Form.Item>

          <Form.Item
            name="full_name"
            label="Full Name"
            rules={[{ required: true, message: 'Please enter full name' }]}
          >
            <Input />
          </Form.Item>

          <Form.Item
            name="password"
            label="Password"
            rules={[
              { required: true, message: 'Please enter password' },
              { min: 6, message: 'Password must be at least 6 characters' }
            ]}
          >
            <Input.Password />
          </Form.Item>

          <Form.Item
            name="role"
            label="Role"
            rules={[{ required: true, message: 'Please select role' }]}
          >
            <Select placeholder="Select role">
              {roles.map((role) => (
                <Option key={role.value} value={role.value}>
                  {role.label}
                  <div style={{ fontSize: '12px', color: '#666' }}>
                    {role.description}
                  </div>
                </Option>
              ))}
            </Select>
          </Form.Item>

          <Alert
            message="Role Permissions"
            description={
              <ul style={{ marginBottom: 0, paddingLeft: 20 }}>
                <li><strong>Admin:</strong> Full system access including user management, portal settings, RADIUS, and IPDR</li>
                <li><strong>IPDR Viewer:</strong> Limited access to view IPDR reports only</li>
              </ul>
            }
            type="info"
            showIcon
            style={{ marginBottom: 16 }}
          />

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

      {/* Edit Admin Modal */}
      <Modal
        title="Edit Admin"
        open={editModalVisible}
        onCancel={() => {
          setEditModalVisible(false);
          editForm.resetFields();
        }}
        footer={null}
        width={700}
      >
        <Form form={editForm} layout="vertical" onFinish={handleUpdateAdmin}>
          <Form.Item
            name="email"
            label="Email"
            rules={[
              { required: true },
              { type: 'email', message: 'Invalid email' }
            ]}
          >
            <Input />
          </Form.Item>

          <Form.Item
            name="full_name"
            label="Full Name"
            rules={[{ required: true }]}
          >
            <Input />
          </Form.Item>

          <Descriptions title="Permissions" bordered column={1} size="small" style={{ marginBottom: 16 }}>
            <Descriptions.Item label="Manage Portal">
              <Form.Item name="can_manage_portal" valuePropName="checked" noStyle>
                <Switch />
              </Form.Item>
            </Descriptions.Item>
            <Descriptions.Item label="Manage Sessions">
              <Form.Item name="can_manage_sessions" valuePropName="checked" noStyle>
                <Switch />
              </Form.Item>
            </Descriptions.Item>
            <Descriptions.Item label="View Records">
              <Form.Item name="can_view_records" valuePropName="checked" noStyle>
                <Switch />
              </Form.Item>
            </Descriptions.Item>
            <Descriptions.Item label="View IPDR">
              <Form.Item name="can_view_ipdr" valuePropName="checked" noStyle>
                <Switch />
              </Form.Item>
            </Descriptions.Item>
            <Descriptions.Item label="Manage RADIUS">
              <Form.Item name="can_manage_radius" valuePropName="checked" noStyle>
                <Switch />
              </Form.Item>
            </Descriptions.Item>
          </Descriptions>

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

      {/* Password Update Modal */}
      <Modal
        title="Update Password"
        open={passwordModalVisible}
        onCancel={() => {
          setPasswordModalVisible(false);
          passwordForm.resetFields();
        }}
        footer={null}
      >
        <p>Update password for: <strong>{selectedAdmin?.username}</strong></p>
        <Form form={passwordForm} layout="vertical" onFinish={handleUpdatePassword}>
          <Form.Item
            name="new_password"
            label="New Password"
            rules={[
              { required: true, message: 'Please enter new password' },
              { min: 6, message: 'Password must be at least 6 characters' }
            ]}
          >
            <Input.Password />
          </Form.Item>

          <Form.Item
            name="confirm_password"
            label="Confirm Password"
            dependencies={['new_password']}
            rules={[
              { required: true, message: 'Please confirm password' },
              ({ getFieldValue }) => ({
                validator(_, value) {
                  if (!value || getFieldValue('new_password') === value) {
                    return Promise.resolve();
                  }
                  return Promise.reject(new Error('Passwords do not match'));
                },
              }),
            ]}
          >
            <Input.Password />
          </Form.Item>

          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">
                Update Password
              </Button>
              <Button onClick={() => {
                setPasswordModalVisible(false);
                passwordForm.resetFields();
              }}>
                Cancel
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default AdminManagement;
