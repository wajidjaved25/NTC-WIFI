import React, { useState, useEffect } from 'react';
import api from '../services/api';
import { Table, Button, Tag, Space, message, Modal, Card, Statistic, Row, Col } from 'antd';
import { ReloadOutlined, DisconnectOutlined, UserDeleteOutlined, ClockCircleOutlined } from '@ant-design/icons';

const RadiusSessions = () => {
  const [sessions, setSessions] = useState([]);
  const [statistics, setStatistics] = useState({});
  const [loading, setLoading] = useState(false);
  const [refreshInterval, setRefreshInterval] = useState(null);

  useEffect(() => {
    loadData();
    // Auto-refresh every 10 seconds
    const interval = setInterval(loadData, 10000);
    setRefreshInterval(interval);
    
    return () => {
      if (interval) clearInterval(interval);
    };
  }, []);

  const loadData = async () => {
    await Promise.all([
      loadActiveSessions(),
      loadStatistics()
    ]);
  };

  const loadActiveSessions = async () => {
    try {
      setLoading(true);
      const response = await api.get('/radius/sessions/active');
      
      if (response.data.success) {
        setSessions(response.data.sessions);
      }
    } catch (error) {
      console.error('Error loading sessions:', error);
      if (error.response?.status !== 403) {
        message.error('Failed to load active sessions');
      }
    } finally {
      setLoading(false);
    }
  };

  const loadStatistics = async () => {
    try {
      const response = await api.get('/radius/statistics');
      
      if (response.data.success) {
        setStatistics(response.data.statistics);
      }
    } catch (error) {
      console.error('Error loading statistics:', error);
    }
  };

  const handleDisconnect = async (username) => {
    Modal.confirm({
      title: 'Disconnect User',
      content: `Are you sure you want to disconnect user ${username}?`,
      okText: 'Yes, Disconnect',
      okType: 'danger',
      cancelText: 'Cancel',
      onOk: async () => {
        try {
          const response = await api.post(`/radius/sessions/disconnect/${username}`);
          
          if (response.data.success) {
            message.success('User disconnected successfully');
            loadData();
          } else {
            message.warning(response.data.message || 'Failed to disconnect user');
          }
        } catch (error) {
          message.error('Error disconnecting user');
          console.error(error);
        }
      }
    });
  };

  const formatBytes = (bytes) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  };

  const formatDuration = (seconds) => {
    if (!seconds) return '0s';
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    
    const parts = [];
    if (hours > 0) parts.push(`${hours}h`);
    if (minutes > 0) parts.push(`${minutes}m`);
    if (secs > 0 || parts.length === 0) parts.push(`${secs}s`);
    
    return parts.join(' ');
  };

  const columns = [
    {
      title: 'Username',
      dataIndex: 'username',
      key: 'username',
      render: (text) => <strong>{text}</strong>
    },
    {
      title: 'IP Address',
      dataIndex: 'ip_address',
      key: 'ip_address',
      render: (text) => text || 'N/A'
    },
    {
      title: 'MAC Address',
      dataIndex: 'mac_address',
      key: 'mac_address',
      render: (text) => text || 'N/A'
    },
    {
      title: 'SSID',
      dataIndex: 'ssid',
      key: 'ssid',
      render: (text) => text || 'N/A'
    },
    {
      title: 'AP Name',
      dataIndex: 'ap_name',
      key: 'ap_name',
      render: (text) => text || 'N/A'
    },
    {
      title: 'Start Time',
      dataIndex: 'start_time',
      key: 'start_time',
      render: (text) => text ? new Date(text).toLocaleString() : 'N/A'
    },
    {
      title: 'Duration',
      dataIndex: 'duration',
      key: 'duration',
      render: (duration) => (
        <Tag color="blue" icon={<ClockCircleOutlined />}>
          {formatDuration(duration)}
        </Tag>
      )
    },
    {
      title: 'Data Usage',
      key: 'data_usage',
      render: (_, record) => (
        <div>
          <div>↓ {formatBytes(record.bytes_in)}</div>
          <div>↑ {formatBytes(record.bytes_out)}</div>
          <strong>Total: {formatBytes(record.bytes_in + record.bytes_out)}</strong>
        </div>
      )
    },
    {
      title: 'Status',
      key: 'status',
      render: () => <Tag color="green">Active</Tag>
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_, record) => (
        <Space>
          <Button
            type="primary"
            danger
            size="small"
            icon={<DisconnectOutlined />}
            onClick={() => handleDisconnect(record.username)}
          >
            Disconnect
          </Button>
        </Space>
      )
    }
  ];

  return (
    <div style={{ padding: '24px' }}>
      <div style={{ marginBottom: '24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h2>Active RADIUS Sessions</h2>
        <Button
          type="primary"
          icon={<ReloadOutlined />}
          onClick={loadData}
          loading={loading}
        >
          Refresh
        </Button>
      </div>

      {/* Statistics Cards */}
      <Row gutter={16} style={{ marginBottom: '24px' }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="Total RADIUS Users"
              value={statistics.total_users || 0}
              prefix={<UserDeleteOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="Active Sessions"
              value={statistics.active_sessions || 0}
              valueStyle={{ color: '#3f8600' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="Sessions Today"
              value={statistics.sessions_today || 0}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="Data Used Today"
              value={formatBytes(statistics.total_data_today || 0)}
            />
          </Card>
        </Col>
      </Row>

      {/* Sessions Table */}
      <Card>
        <Table
          columns={columns}
          dataSource={sessions}
          rowKey="session_id"
          loading={loading}
          scroll={{ x: 1200 }}
          pagination={{
            pageSize: 10,
            showTotal: (total) => `Total ${total} active sessions`
          }}
        />
      </Card>

      <div style={{ marginTop: '16px', color: '#888', fontSize: '12px' }}>
        Auto-refreshing every 10 seconds. Last updated: {new Date().toLocaleTimeString()}
      </div>
    </div>
  );
};

export default RadiusSessions;
