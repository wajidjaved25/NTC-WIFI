import React, { useState, useEffect } from 'react';
import {
  Table,
  Button,
  Modal,
  Form,
  Input,
  Select,
  Tag,
  Space,
  Popconfirm,
  message,
  Card,
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  LockOutlined,
  UnlockOutlined,
} from '@ant-design/icons';
import api from '../services/api';
import dayjs from 'dayjs';

const { Option } = Select;

const AdminManagement = () => {
  const [loading, setLoading] = useState(false);
  const [admins, setAdmins] = useState([]);
  const [modalVisible, setModalVisible] = useState(false);
  const [editingAdmin, setEditingAdmin] = useState(null);
  const [form] = Form.useForm();

  useEffect(() => {
    fetchAdmins();
  }, []);

  const fetchAdmins = async () => {
    setLoading(true);
    try {
      const response = await api.get('/auth/admins');
      setAdmins(response.data.admins || []);
    } catch (error) {
      console.error('Failed to fetch admins:', error);
      message.error('Failed to load administrators');
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = () => {
    setEditingAdmin(null);
    form.resetFields();
    setModalVisible(true);
  };

  const handleEdit = (admin) => {
    setEditingAdmin(admin);
    form.setFieldsValue({
      username: admin.username,
      full_name: admin.full_name,
      email: admin.email,
      mobile: admin.mobile,
      role: admin.role,
    });
    setModalVisible(true);
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      
      if (editingAdmin) {
        // Update admin
        await api.put(`/auth/admins/${editingAdmin.id}`, values);
        message.success('Administrator updated successfully!');
      } else {
        // Create new admin
        await api.post('/auth/create-admin', values);
        message.success('Administrator created successfully!');
      }
      
      setModalVisible(false);
      form.resetFields();
      fetchAdmins();
    } catch (error) {
      console.error('Failed to save admin:', error);
      message.error('Failed to save administrator: ' + (error.response?.data?.detail || 'Unknown error'));
    }
  };

  const handleToggleActive = async (adminId, isActive) => {
    try {
      if (isActive) {
        await api.patch(`/auth/admins/${adminId}/activate`);
        message.success('Administrator activated');
      } else {
        await api.patch(`/auth/admins/${adminId}/deactivate`);
        message.success('Administrator deactivated');
      }
      fetchAdmins();
    } catch (error) {
      console.error('Failed to toggle admin status:', error);
      message.error('Failed to update status');
    }
  };

  const handleDelete = async (adminId) => {
    try {
      await api.delete(`/auth/admins/${adminId}`);
      message.success('Administrator deleted successfully');
      fetchAdmins();
    } catch (error) {
      console.error('Failed to delete admin:', error);
      message.error('Failed to delete administrator');
    }
  };

  const getRoleColor = (role) => {
    const colors = {
      superadmin: 'red',
      admin: 'blue',
      reports_user: 'green',
      ads_user: 'orange',
    };
    return colors[role] || 'default';
  };

  const getRoleLabel = (role) => {
    const labels = {
      superadmin: 'Super Admin',
      admin: 'Admin',
      reports_user: 'Reports User',
      ads_user: 'Ads User',
    };
    return labels[role] || role;
  };

  const columns = [
    {
      title: 'Username',
      dataIndex: 'username',
      key: 'username',
      sorter: (a, b) => a.username.localeCompare(b.username),
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
      render: (role) => <Tag color={getRoleColor(role)}>{getRoleLabel(role)}</Tag>,
      filters: [
        { text: 'Admin', value: 'admin' },
        { text: 'Reports User', value: 'reports_user' },
        { text: 'Ads User', value: 'ads_user' },
      ],
      onFilter: (value, record) => record.role === value,
    },
    {
      title: 'Mobile',
      dataIndex: 'mobile',
      key: 'mobile',
      render: (mobile) => mobile || 'N/A',
    },
    {
      title: 'Email',
      dataIndex: 'email',
      key: 'email',
      render: (email) => email || 'N/A',
    },
    {
      title: 'Status',
      dataIndex: 'is_active',
      key: 'is_active',
      render: (isActive) => (
        <Tag color={isActive ? 'success' : 'default'}>
          {isActive ? 'Active' : 'Inactive'}
        </Tag>
      ),
      filters: [
        { text: 'Active', value: true },
        { text: 'Inactive', value: false },
      ],
      onFilter: (value, record) => record.is_active === value,
    },
    {
      title: 'Last Login',
      dataIndex: 'last_login',
      key: 'last_login',
      render: (date) => date ? dayjs(date).format('YYYY-MM-DD HH:mm') : 'Never',
      sorter: (a, b) => {
        if (!a.last_login) return 1;
        if (!b.last_login) return -1;
        return new Date(a.last_login) - new Date(b.last_login);
      },
    },
    {
      title: 'Created',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date) => dayjs(date).format('YYYY-MM-DD'),
      sorter: (a, b) => new Date(a.created_at) - new Date(b.created_at),
    },
    {
      title: 'Actions',
      key: 'actions',
      fixed: 'right',
      width: 180,
      render: (_, record) => (
        <Space>
          <Button
            icon={<EditOutlined />}
            size="small"
            onClick={() => handleEdit(record)}
          />
          <Button
            icon={record.is_active ? <LockOutlined /> : <UnlockOutlined />}
            size="small"
            onClick={() => handleToggleActive(record.id, !record.is_active)}
          />
          <Popconfirm
            title="Delete this administrator?"
            description="This action cannot be undone."
            onConfirm={() => handleDelete(record.id)}
            okText="Yes"
            cancelText="No"
          >
            <Button danger icon={<DeleteOutlined />} size="small" />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div className="admin-management">
      <Card>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
          <div>
            <h2>Administrator Management</h2>
            <p style={{ color: '#666', margin: 0 }}>
              Manage admin users and their roles.
            </p>
          </div>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={handleCreate}
          >
            Add Administrator
          </Button>
        </div>

        <Table
          columns={columns}
          dataSource={admins}
          loading={loading}
          rowKey="id"
          pagination={{
            showSizeChanger: true,
            showTotal: (total) => `Total ${total} administrators`,
          }}
        />
      </Card>

      {/* Create/Edit Modal */}
      <Modal
        title={editingAdmin ? 'Edit Administrator' : 'Add New Administrator'}
        open={modalVisible}
        onCancel={() => {
          setModalVisible(false);
          form.resetFields();
        }}
        onOk={handleSubmit}
        width={600}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            label="Username"
            name="username"
            rules={[
              { required: true, message: 'Please enter username' },
              { min: 3, message: 'Username must be at least 3 characters' },
            ]}
          >
            <Input placeholder="Enter username" disabled={!!editingAdmin} />
          </Form.Item>

          <Form.Item
            label="Full Name"
            name="full_name"
            rules={[{ required: true, message: 'Please enter full name' }]}
          >
            <Input placeholder="Enter full name" />
          </Form.Item>

          <Form.Item
            label="Role"
            name="role"
            rules={[{ required: true, message: 'Please select role' }]}
          >
            <Select placeholder="Select role">
              <Option value="admin">Admin (Full Access)</Option>
              <Option value="reports_user">Reports User (OTP Login)</Option>
              <Option value="ads_user">Ads User (OTP Login)</Option>
            </Select>
          </Form.Item>

          <Form.Item
            noStyle
            shouldUpdate={(prevValues, currentValues) => prevValues.role !== currentValues.role}
          >
            {({ getFieldValue }) =>
              ['reports_user', 'ads_user'].includes(getFieldValue('role')) ? (
                <Form.Item
                  label="Mobile Number"
                  name="mobile"
                  rules={[
                    { required: true, message: 'Mobile number required for OTP login' },
                    { pattern: /^\d{10,15}$/, message: 'Invalid mobile number' },
                  ]}
                >
                  <Input placeholder="Enter mobile number" />
                </Form.Item>
              ) : null
            }
          </Form.Item>

          <Form.Item
            noStyle
            shouldUpdate={(prevValues, currentValues) => prevValues.role !== currentValues.role}
          >
            {({ getFieldValue }) =>
              getFieldValue('role') === 'admin' && !editingAdmin ? (
                <Form.Item
                  label="Password"
                  name="password"
                  rules={[
                    { required: true, message: 'Please enter password' },
                    { min: 8, message: 'Password must be at least 8 characters' },
                  ]}
                >
                  <Input.Password placeholder="Enter password" />
                </Form.Item>
              ) : null
            }
          </Form.Item>

          <Form.Item label="Email" name="email">
            <Input placeholder="Enter email (optional)" type="email" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default AdminManagement;
