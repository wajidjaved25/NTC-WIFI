import React from 'react';
import { Card, Row, Col, Empty } from 'antd';
import { LineChart, Line, BarChart, Bar, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

const COLORS = ['#1890ff', '#52c41a', '#faad14', '#f5222d', '#722ed1', '#13c2c2'];

const Charts = ({ sessionTrends, userData, peakHours, loading }) => {
  // Format session trends data
  const formattedTrends = sessionTrends.map(item => ({
    date: new Date(item.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
    sessions: item.sessions || 0
  }));

  // Format peak hours data
  const formattedPeakHours = peakHours.map(item => ({
    hour: `${String(item.hour).padStart(2, '0')}:00`,
    sessions: item.sessions || 0
  }));

  return (
    <Row gutter={[16, 16]} style={{ marginTop: '16px' }}>
      {/* Session Trends Chart */}
      <Col xs={24} lg={16}>
        <Card title="Session Trends (Last 7 Days)" loading={loading} bordered={false}>
          {formattedTrends.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={formattedTrends}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Line 
                  type="monotone" 
                  dataKey="sessions" 
                  stroke="#1890ff" 
                  strokeWidth={3}
                  name="Sessions"
                  dot={{ fill: '#1890ff', r: 5 }}
                  activeDot={{ r: 7 }}
                />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <Empty 
              description="No session data available" 
              style={{ padding: '60px 0' }}
            />
          )}
        </Card>
      </Col>

      {/* User Distribution Pie Chart */}
      <Col xs={24} lg={8}>
        <Card title="User Distribution" loading={loading} bordered={false}>
          {userData && userData.some(d => d.value > 0) ? (
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={userData}
                  cx="50%"
                  cy="50%"
                  labelLine={true}
                  label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {userData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <Empty 
              description="No user data available" 
              style={{ padding: '60px 0' }}
            />
          )}
        </Card>
      </Col>

      {/* Peak Hours Bar Chart */}
      <Col xs={24}>
        <Card title="Peak Hours (Last 7 Days)" loading={loading} bordered={false}>
          {formattedPeakHours.length > 0 ? (
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={formattedPeakHours}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="hour" />
                <YAxis />
                <Tooltip />
                <Bar 
                  dataKey="sessions" 
                  fill="#1890ff" 
                  name="Sessions"
                  radius={[8, 8, 0, 0]}
                />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <Empty 
              description="No peak hour data available" 
              style={{ padding: '60px 0' }}
            />
          )}
        </Card>
      </Col>
    </Row>
  );
};

export default Charts;
