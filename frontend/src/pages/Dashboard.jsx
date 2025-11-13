import React, { useState, useEffect } from 'react';
import { message, Button } from 'antd';
import { ReloadOutlined } from '@ant-design/icons';
import StatsCards from '../components/Dashboard/StatsCards';
import Charts from '../components/Dashboard/Charts';
import RealtimeStats from '../components/Dashboard/RealtimeStats';
import api from '../services/api';
import './Dashboard.css';

const Dashboard = () => {
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [stats, setStats] = useState(null);
  const [sessionTrends, setSessionTrends] = useState([]);
  const [userData, setUserData] = useState([]);
  const [peakHours, setPeakHours] = useState([]);
  const [realtimeStats, setRealtimeStats] = useState(null);
  const [lastUpdate, setLastUpdate] = useState(new Date());

  useEffect(() => {
    fetchDashboardData();
    // Refresh every 60 seconds for stats
    const interval = setInterval(fetchDashboardData, 60000);
    // Refresh real-time stats every 10 seconds
    const realtimeInterval = setInterval(fetchRealtimeStats, 10000);
    
    return () => {
      clearInterval(interval);
      clearInterval(realtimeInterval);
    };
  }, []);

  const fetchDashboardData = async (showLoading = true) => {
    if (showLoading) setLoading(true);
    try {
      // Fetch all dashboard data in parallel
      const [statsRes, trendsRes, peakRes, realtimeRes] = await Promise.all([
        api.get('/dashboard/stats?days=30'),
        api.get('/dashboard/session-trends?days=7'),
        api.get('/dashboard/peak-hours?days=7'),
        api.get('/dashboard/real-time'),
      ]);

      setStats(statsRes.data);
      setSessionTrends(trendsRes.data.trends || []);
      setPeakHours(peakRes.data.data || []);
      setRealtimeStats(realtimeRes.data);
      
      // Calculate user data for pie chart
      if (statsRes.data) {
        setUserData([
          { name: 'New Users', value: statsRes.data.newUsers || 0 },
          { name: 'Returning Users', value: statsRes.data.returningUsers || 0 },
          { name: 'Blocked Users', value: statsRes.data.blockedUsers || 0 },
        ]);
      }
      
      setLastUpdate(new Date());
    } catch (error) {
      console.error('Dashboard error:', error);
      message.error('Failed to load dashboard data');
      
      // Set empty data on error
      setStats({
        totalUsers: 0,
        activeSessions: 0,
        todaySessions: 0,
        totalDataUsage: 0,
        newUsers: 0,
        returningUsers: 0,
        blockedUsers: 0,
        activeAds: 0,
        adViews: 0,
        averageSessionDuration: 0,
      });
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const fetchRealtimeStats = async () => {
    try {
      const res = await api.get('/dashboard/real-time');
      setRealtimeStats(res.data);
      setLastUpdate(new Date());
    } catch (error) {
      console.error('Real-time stats error:', error);
    }
  };

  const handleRefresh = () => {
    setRefreshing(true);
    fetchDashboardData(false);
  };

  return (
    <div className="dashboard">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <div>
          <h2 style={{ margin: 0 }}>Dashboard Overview</h2>
          <p style={{ color: '#666', margin: '4px 0 0 0', fontSize: '14px' }}>
            Last updated: {lastUpdate.toLocaleTimeString()}
          </p>
        </div>
        <Button 
          icon={<ReloadOutlined spin={refreshing} />} 
          onClick={handleRefresh}
          loading={refreshing}
        >
          Refresh
        </Button>
      </div>
      
      {/* Real-time Stats */}
      <RealtimeStats stats={realtimeStats} loading={loading} />
      
      {/* Main Stats Cards */}
      <StatsCards stats={stats} loading={loading} />
      
      {/* Charts */}
      <Charts 
        sessionTrends={sessionTrends} 
        userData={userData}
        peakHours={peakHours}
        loading={loading}
      />
    </div>
  );
};

export default Dashboard;
