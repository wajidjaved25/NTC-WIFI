import React from 'react';
import { Card, Row, Col, Statistic, Badge, Tag } from 'antd';
import { WifiOutlined, DashboardOutlined } from '@ant-design/icons';

const RealtimeStats = ({ stats, loading }) => {
  if (!stats || loading) return null;

  return (
    <Card 
      title={
        <span>
          <Badge status="processing" style={{ marginRight: 8 }} />
          Real-Time Activity
        </span>
      }
      style={{ marginBottom: 16 }}
      bordered={false}
    >
      <Row gutter={16}>
        <Col span={8}>
          <Statistic
            title="Active Sessions Now"
            value={stats.active_sessions || 0}
            prefix={<WifiOutlined />}
            valueStyle={{ color: '#52c41a' }}
          />
        </Col>
        <Col span={8}>
          <Statistic
            title="Sessions Today"
            value={stats.today?.sessions || 0}
            prefix={<DashboardOutlined />}
          />
        </Col>
        <Col span={8}>
          <Statistic
            title="Data Usage Today"
            value={((stats.today?.data_usage || 0) / (1024 * 1024 * 1024)).toFixed(2)}
            suffix="GB"
          />
        </Col>
      </Row>

      {stats.sessions_by_ap && stats.sessions_by_ap.length > 0 && (
        <div style={{ marginTop: 16 }}>
          <p style={{ marginBottom: 8, color: '#666', fontSize: '14px' }}>
            Active by Access Point:
          </p>
          <div>
            {stats.sessions_by_ap.map((ap, index) => (
              <Tag key={index} color="blue" style={{ marginBottom: 4 }}>
                {ap.ap || 'Unknown'}: {ap.count} sessions
              </Tag>
            ))}
          </div>
        </div>
      )}
    </Card>
  );
};

export default RealtimeStats;
