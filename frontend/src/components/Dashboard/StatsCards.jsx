import React from 'react';
import { Card, Row, Col, Statistic } from 'antd';
import { 
  UserOutlined, 
  WifiOutlined, 
  ClockCircleOutlined, 
  CloudDownloadOutlined,
  UserAddOutlined,
  EyeOutlined,
  HourglassOutlined,
  StopOutlined
} from '@ant-design/icons';
import './StatsCards.css';

const StatsCards = ({ stats, loading }) => {
  const formatBytes = (bytes) => {
    if (!bytes) return 0;
    return (bytes / (1024 * 1024 * 1024)).toFixed(2); // Convert to GB
  };

  const formatDuration = (seconds) => {
    if (!seconds) return '0m';
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return `${minutes}m`;
    const hours = Math.floor(minutes / 60);
    const remainingMinutes = minutes % 60;
    return `${hours}h ${remainingMinutes}m`;
  };

  const cards = [
    {
      title: 'Total Users',
      value: stats?.totalUsers || 0,
      icon: <UserOutlined />,
      color: '#1890ff',
    },
    {
      title: 'New Users (30d)',
      value: stats?.newUsers || 0,
      icon: <UserAddOutlined />,
      color: '#52c41a',
    },
    {
      title: 'Active Sessions',
      value: stats?.activeSessions || 0,
      icon: <WifiOutlined />,
      color: '#faad14',
    },
    {
      title: 'Blocked Users',
      value: stats?.blockedUsers || 0,
      icon: <StopOutlined />,
      color: '#f5222d',
    },
    {
      title: 'Sessions (30d)',
      value: stats?.todaySessions || 0,
      icon: <ClockCircleOutlined />,
      color: '#722ed1',
    },
    {
      title: 'Data Usage (30d)',
      value: formatBytes(stats?.totalDataUsage),
      icon: <CloudDownloadOutlined />,
      color: '#13c2c2',
      suffix: 'GB',
    },
    {
      title: 'Active Ads',
      value: stats?.activeAds || 0,
      icon: <EyeOutlined />,
      color: '#eb2f96',
    },
    {
      title: 'Avg. Session Time',
      value: formatDuration(stats?.averageSessionDuration),
      icon: <HourglassOutlined />,
      color: '#fa8c16',
      isFormatted: true,
    },
  ];

  return (
    <Row gutter={[16, 16]}>
      {cards.map((card, index) => (
        <Col xs={24} sm={12} lg={6} key={index}>
          <Card 
            className="stats-card" 
            loading={loading}
            bordered={false}
            style={{ borderTop: `3px solid ${card.color}` }}
          >
            <Statistic
              title={card.title}
              value={card.isFormatted ? undefined : card.value}
              formatter={card.isFormatted ? () => card.value : undefined}
              prefix={<span style={{ color: card.color, fontSize: '24px' }}>{card.icon}</span>}
              suffix={card.suffix}
              valueStyle={{ fontWeight: 'bold', fontSize: '24px' }}
            />
          </Card>
        </Col>
      ))}
    </Row>
  );
};

export default StatsCards;
