import React, { useState, useEffect } from 'react';
import { message, Modal, Descriptions, Tag } from 'antd';
import RecordsFilters from '../components/Records/RecordsFilters';
import RecordsTable from '../components/Records/RecordsTable';
import api from '../services/api';
import dayjs from 'dayjs';

const Records = () => {
  const [loading, setLoading] = useState(false);
  const [records, setRecords] = useState([]);
  const [pagination, setPagination] = useState({
    current: 1,
    pageSize: 25,
    total: 0,
  });
  const [filters, setFilters] = useState({});
  const [selectedRecord, setSelectedRecord] = useState(null);
  const [detailsVisible, setDetailsVisible] = useState(false);

  useEffect(() => {
    fetchRecords();
  }, [pagination.current, pagination.pageSize, filters]);

  const fetchRecords = async () => {
    setLoading(true);
    try {
      const params = {
        page: pagination.current,
        page_size: pagination.pageSize,
        ...filters,
      };

      const response = await api.get('/records/sessions', { params });
      
      // Backend returns 'sessions' not 'records'
      const sessions = response.data.sessions || [];
      
      // Transform to match frontend structure
      const transformedRecords = sessions.map(session => ({
        ...session,
        user: {
          name: session.user_name,
          mobile: session.user_mobile,
          cnic: session.user_cnic,
          passport: session.user_passport,
          email: session.user_email,
          id_type: session.user_id_type
        }
      }));
      
      setRecords(transformedRecords);
      setPagination(prev => ({
        ...prev,
        total: response.data.total_count || 0,
      }));
    } catch (error) {
      console.error('Failed to fetch records:', error);
      message.error('Failed to load records');
    } finally {
      setLoading(false);
    }
  };

  const handleFilter = (newFilters) => {
    setFilters(newFilters);
    setPagination(prev => ({ ...prev, current: 1 }));
  };

  const handleReset = () => {
    setFilters({});
    setPagination(prev => ({ ...prev, current: 1 }));
  };

  const handleTableChange = (newPagination, tableFilters, sorter) => {
    setPagination(prev => ({
      ...prev,
      current: newPagination.current,
      pageSize: newPagination.pageSize,
    }));

    // Handle sorting
    if (sorter.field) {
      setFilters(prev => ({
        ...prev,
        sort_by: sorter.field,
        sort_order: sorter.order === 'ascend' ? 'asc' : 'desc',
      }));
    }

    // Handle table filters (status, etc.)
    if (tableFilters.session_status) {
      setFilters(prev => ({
        ...prev,
        status: tableFilters.session_status[0],
      }));
    }
  };

  const handleExport = async (format) => {
    try {
      message.loading(`Exporting to ${format.toUpperCase()}...`, 0);
      
      const response = await api.get(`/records/export/${format}`, {
        params: filters,
        responseType: 'blob',
      });

      // Create download link
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `sessions_${dayjs().format('YYYY-MM-DD')}.${format}`);
      document.body.appendChild(link);
      link.click();
      link.remove();

      message.destroy();
      message.success(`Exported successfully!`);
    } catch (error) {
      message.destroy();
      console.error('Export failed:', error);
      message.error('Failed to export records');
    }
  };

  const handleViewDetails = (record) => {
    setSelectedRecord(record);
    setDetailsVisible(true);
  };

  const formatBytes = (bytes) => {
    if (!bytes || bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${(bytes / Math.pow(k, i)).toFixed(2)} ${sizes[i]}`;
  };

  const formatDuration = (seconds) => {
    if (!seconds) return '0s';
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    
    if (hours > 0) return `${hours}h ${minutes}m ${secs}s`;
    if (minutes > 0) return `${minutes}m ${secs}s`;
    return `${secs}s`;
  };

  return (
    <div className="records">
      <h2>Session Records</h2>
      <p style={{ marginBottom: 24, color: '#666' }}>
        View, filter, and export WiFi session records.
      </p>

      <RecordsFilters
        onFilter={handleFilter}
        onReset={handleReset}
        loading={loading}
      />

      <RecordsTable
        data={records}
        loading={loading}
        pagination={pagination}
        onChange={handleTableChange}
        onExport={handleExport}
        onViewDetails={handleViewDetails}
      />

      {/* Details Modal */}
      <Modal
        title="Session Details"
        open={detailsVisible}
        onCancel={() => setDetailsVisible(false)}
        footer={null}
        width={700}
      >
        {selectedRecord && (
          <Descriptions bordered column={2}>
            <Descriptions.Item label="User Name" span={2}>
              {selectedRecord.user?.name || 'N/A'}
            </Descriptions.Item>
            <Descriptions.Item label="Mobile">
              {selectedRecord.user?.mobile || 'N/A'}
            </Descriptions.Item>
            <Descriptions.Item label="Email">
              {selectedRecord.user?.email || 'N/A'}
            </Descriptions.Item>
            <Descriptions.Item label="ID Type">
              {selectedRecord.user?.id_type?.toUpperCase() || 'N/A'}
            </Descriptions.Item>
            <Descriptions.Item label="CNIC">
              {selectedRecord.user?.cnic || 'N/A'}
            </Descriptions.Item>
            <Descriptions.Item label="Passport">
              {selectedRecord.user?.passport || 'N/A'}
            </Descriptions.Item>
            <Descriptions.Item label="MAC Address">
              <code>{selectedRecord.mac_address}</code>
            </Descriptions.Item>
            <Descriptions.Item label="IP Address">
              {selectedRecord.ip_address || 'N/A'}
            </Descriptions.Item>
            <Descriptions.Item label="Start Time" span={2}>
              {dayjs(selectedRecord.start_time).format('YYYY-MM-DD HH:mm:ss')}
            </Descriptions.Item>
            <Descriptions.Item label="End Time" span={2}>
              {selectedRecord.end_time 
                ? dayjs(selectedRecord.end_time).format('YYYY-MM-DD HH:mm:ss')
                : 'Active'}
            </Descriptions.Item>
            <Descriptions.Item label="Duration">
              {formatDuration(selectedRecord.duration)}
            </Descriptions.Item>
            <Descriptions.Item label="Status">
              <Tag color={
                selectedRecord.session_status === 'active' ? 'green' :
                selectedRecord.session_status === 'completed' ? 'blue' : 'red'
              }>
                {selectedRecord.session_status?.toUpperCase()}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="Data Upload">
              {formatBytes(selectedRecord.data_upload)}
            </Descriptions.Item>
            <Descriptions.Item label="Data Download">
              {formatBytes(selectedRecord.data_download)}
            </Descriptions.Item>
            <Descriptions.Item label="Total Data" span={2}>
              {formatBytes(selectedRecord.total_data)}
            </Descriptions.Item>
            <Descriptions.Item label="SSID">
              {selectedRecord.ssid || 'N/A'}
            </Descriptions.Item>
            <Descriptions.Item label="AP Name">
              {selectedRecord.ap_name || 'N/A'}
            </Descriptions.Item>
            <Descriptions.Item label="AP MAC">
              {selectedRecord.ap_mac || 'N/A'}
            </Descriptions.Item>
            <Descriptions.Item label="Site">
              {selectedRecord.site || 'N/A'}
            </Descriptions.Item>
            <Descriptions.Item label="Disconnect Reason" span={2}>
              {selectedRecord.disconnect_reason || 'N/A'}
            </Descriptions.Item>
          </Descriptions>
        )}
      </Modal>
    </div>
  );
};

export default Records;
