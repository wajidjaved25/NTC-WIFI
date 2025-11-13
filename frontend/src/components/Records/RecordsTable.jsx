import React, { useState } from 'react';
import { Table, Tag, Button, Space, Tooltip } from 'antd';
import { DownloadOutlined, EyeOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import duration from 'dayjs/plugin/duration';

dayjs.extend(duration);

const RecordsTable = ({ data, loading, pagination, onChange, onExport, onViewDetails }) => {
  const formatBytes = (bytes) => {
    if (!bytes || bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${(bytes / Math.pow(k, i)).toFixed(2)} ${sizes[i]}`;
  };

  const formatDuration = (seconds) => {
    if (!seconds) return '0s';
    const d = dayjs.duration(seconds, 'seconds');
    const hours = Math.floor(d.asHours());
    const minutes = d.minutes();
    const secs = d.seconds();
    
    if (hours > 0) return `${hours}h ${minutes}m`;
    if (minutes > 0) return `${minutes}m ${secs}s`;
    return `${secs}s`;
  };

  const getStatusColor = (status) => {
    const colors = {
      'active': 'green',
      'completed': 'blue',
      'terminated': 'red',
      'timeout': 'orange',
    };
    return colors[status] || 'default';
  };

  const columns = [
    {
      title: 'User Name',
      dataIndex: ['user', 'name'],
      key: 'userName',
      fixed: 'left',
      width: 150,
      sorter: true,
    },
    {
      title: 'Mobile',
      dataIndex: ['user', 'mobile'],
      key: 'mobile',
      width: 130,
    },
    {
      title: 'CNIC',
      dataIndex: ['user', 'cnic'],
      key: 'cnic',
      width: 150,
      render: (cnic) => cnic || '-',
    },
    {
      title: 'Passport',
      dataIndex: ['user', 'passport'],
      key: 'passport',
      width: 120,
      render: (passport) => passport || '-',
    },
    {
      title: 'MAC Address',
      dataIndex: 'mac_address',
      key: 'macAddress',
      width: 150,
      render: (mac) => <code>{mac}</code>,
    },
    {
      title: 'IP Address',
      dataIndex: 'ip_address',
      key: 'ipAddress',
      width: 130,
    },
    {
      title: 'Start Time',
      dataIndex: 'start_time',
      key: 'startTime',
      width: 180,
      sorter: true,
      render: (time) => dayjs(time).format('YYYY-MM-DD HH:mm:ss'),
    },
    {
      title: 'End Time',
      dataIndex: 'end_time',
      key: 'endTime',
      width: 180,
      render: (time) => time ? dayjs(time).format('YYYY-MM-DD HH:mm:ss') : '-',
    },
    {
      title: 'Duration',
      dataIndex: 'duration',
      key: 'duration',
      width: 100,
      sorter: true,
      render: (duration) => formatDuration(duration),
    },
    {
      title: 'Data Usage',
      key: 'dataUsage',
      width: 120,
      sorter: true,
      render: (_, record) => (
        <Tooltip title={`↑ ${formatBytes(record.data_upload)} / ↓ ${formatBytes(record.data_download)}`}>
          {formatBytes(record.total_data)}
        </Tooltip>
      ),
    },
    {
      title: 'SSID',
      dataIndex: 'ssid',
      key: 'ssid',
      width: 150,
    },
    {
      title: 'AP Name',
      dataIndex: 'ap_name',
      key: 'apName',
      width: 150,
    },
    {
      title: 'Status',
      dataIndex: 'session_status',
      key: 'status',
      width: 110,
      filters: [
        { text: 'Active', value: 'active' },
        { text: 'Completed', value: 'completed' },
        { text: 'Terminated', value: 'terminated' },
      ],
      render: (status) => (
        <Tag color={getStatusColor(status)}>
          {status?.toUpperCase()}
        </Tag>
      ),
    },
    {
      title: 'Disconnect Reason',
      dataIndex: 'disconnect_reason',
      key: 'disconnectReason',
      width: 150,
      render: (reason) => reason || '-',
    },
    {
      title: 'Action',
      key: 'action',
      fixed: 'right',
      width: 80,
      render: (_, record) => (
        <Button
          type="link"
          icon={<EyeOutlined />}
          onClick={() => onViewDetails(record)}
          size="small"
        >
          View
        </Button>
      ),
    },
  ];

  return (
    <div className="records-table">
      <div className="table-actions" style={{ marginBottom: 16, textAlign: 'right' }}>
        <Space>
          <Button
            icon={<DownloadOutlined />}
            onClick={() => onExport('excel')}
          >
            Export Excel
          </Button>
          <Button
            icon={<DownloadOutlined />}
            onClick={() => onExport('pdf')}
          >
            Export PDF
          </Button>
        </Space>
      </div>

      <Table
        columns={columns}
        dataSource={data}
        loading={loading}
        pagination={{
          ...pagination,
          showSizeChanger: true,
          showTotal: (total) => `Total ${total} records`,
          pageSizeOptions: ['10', '25', '50', '100'],
        }}
        onChange={onChange}
        scroll={{ x: 2100 }}
        rowKey="id"
        size="small"
      />
    </div>
  );
};

export default RecordsTable;
