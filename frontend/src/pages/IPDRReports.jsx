import { useState, useEffect } from 'react';
import {
  Card,
  Form,
  Input,
  Select,
  DatePicker,
  Button,
  Table,
  Space,
  message,
  Statistic,
  Row,
  Col,
  Upload,
  Modal,
  Tag,
  Descriptions,
  Tooltip
} from 'antd';
import {
  SearchOutlined,
  DownloadOutlined,
  UploadOutlined,
  FileTextOutlined,
  HistoryOutlined,
  DatabaseOutlined
} from '@ant-design/icons';
import { ipdrAPI } from '../services/api';
import dayjs from 'dayjs';

const { RangePicker } = DatePicker;
const { Option } = Select;

const IPDRReports = () => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [searchResults, setSearchResults] = useState([]);
  const [pagination, setPagination] = useState({
    current: 1,
    pageSize: 50,
    total: 0,
  });
  const [searchType, setSearchType] = useState('mobile');
  const [stats, setStats] = useState(null);
  const [importModalVisible, setImportModalVisible] = useState(false);
  const [importJobs, setImportJobs] = useState([]);
  const [lastSearchParams, setLastSearchParams] = useState(null);
  const [syslogStatus, setSyslogStatus] = useState(null);

  useEffect(() => {
    fetchStats();
    fetchImportJobs();
    fetchSyslogStatus();
    
    // Poll syslog status every 30 seconds
    const interval = setInterval(fetchSyslogStatus, 30000);
    return () => clearInterval(interval);
  }, []);

  const fetchStats = async () => {
    try {
      const response = await ipdrAPI.getStats();
      setStats(response.data);
    } catch (error) {
      console.error('Error fetching IPDR stats:', error);
    }
  };

  const fetchImportJobs = async () => {
    try {
      const response = await ipdrAPI.getImportJobs(10);
      setImportJobs(response.data);
    } catch (error) {
      console.error('Error fetching import jobs:', error);
    }
  };

  const fetchSyslogStatus = async () => {
    try {
      const response = await ipdrAPI.getSyslogStatus();
      setSyslogStatus(response.data);
    } catch (error) {
      console.error('Error fetching syslog status:', error);
    }
  };

  const handleRestartSyslog = async () => {
    try {
      await ipdrAPI.restartSyslog();
      message.success('Syslog receiver restarted successfully');
      fetchSyslogStatus();
    } catch (error) {
      message.error('Failed to restart syslog receiver');
      console.error('Restart error:', error);
    }
  };

  const handleSearch = async (values) => {
    setLoading(true);
    try {
      const searchParams = {
        search_type: searchType,
        page: pagination.current,
        page_size: pagination.pageSize,
      };

      // Add search-specific fields
      if (searchType === 'mobile' && values.mobile) {
        searchParams.mobile = values.mobile;
      } else if (searchType === 'cnic' && values.cnic) {
        searchParams.cnic = values.cnic;
      } else if (searchType === 'passport' && values.passport) {
        searchParams.passport = values.passport;
      } else if (searchType === 'ip' && values.ip_address) {
        searchParams.ip_address = values.ip_address;
      } else if (searchType === 'mac' && values.mac_address) {
        searchParams.mac_address = values.mac_address;
      } else if (searchType === 'date_range' && values.dateRange) {
        searchParams.start_date = values.dateRange[0].toISOString();
        searchParams.end_date = values.dateRange[1].toISOString();
      }

      setLastSearchParams(searchParams);
      const response = await ipdrAPI.searchRecords(searchParams);
      
      setSearchResults(response.data.records);
      setPagination({
        ...pagination,
        total: response.data.total_records,
        current: response.data.page,
      });

      message.success(`Found ${response.data.total_records} records`);
    } catch (error) {
      message.error('Failed to search IPDR records');
      console.error('Search error:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleTableChange = (newPagination) => {
    setPagination(newPagination);
    if (lastSearchParams) {
      const updatedParams = {
        ...lastSearchParams,
        page: newPagination.current,
        page_size: newPagination.pageSize,
      };
      ipdrAPI.searchRecords(updatedParams).then(response => {
        setSearchResults(response.data.records);
        setPagination({
          ...newPagination,
          total: response.data.total_records,
        });
      }).catch(error => {
        message.error('Failed to fetch page');
        console.error(error);
      });
    }
  };

  const handleExport = async (format = 'csv') => {
    if (!lastSearchParams) {
      message.warning('Please perform a search first');
      return;
    }

    try {
      const response = await ipdrAPI.exportRecords({
        search_params: lastSearchParams,
        format: format,
      });

      // Create blob and download
      const blob = new Blob([response.data], {
        type: format === 'csv' ? 'text/csv' : 'application/pdf'
      });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `ipdr_report_${dayjs().format('YYYYMMDD_HHmmss')}.${format}`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);

      message.success('Report exported successfully');
    } catch (error) {
      message.error('Failed to export report');
      console.error('Export error:', error);
    }
  };

  const handleCSVImport = async (file) => {
    const formData = new FormData();
    formData.append('file', file);

    try {
      setLoading(true);
      const response = await ipdrAPI.importCSV(formData);
      message.success(`Import started: ${response.data.filename}`);
      setImportModalVisible(false);
      fetchImportJobs();
      fetchStats();
    } catch (error) {
      message.error('Failed to import CSV');
      console.error('Import error:', error);
    } finally {
      setLoading(false);
    }

    return false; // Prevent default upload behavior
  };

  const renderSearchFields = () => {
    switch (searchType) {
      case 'mobile':
        return (
          <Form.Item
            name="mobile"
            label="Mobile Number"
            rules={[{ required: true, message: 'Please enter mobile number' }]}
          >
            <Input placeholder="e.g., 03001234567" prefix="+92" />
          </Form.Item>
        );
      case 'cnic':
        return (
          <Form.Item
            name="cnic"
            label="CNIC Number"
            rules={[{ required: true, message: 'Please enter CNIC number' }]}
          >
            <Input placeholder="e.g., 12345-1234567-1" />
          </Form.Item>
        );
      case 'passport':
        return (
          <Form.Item
            name="passport"
            label="Passport Number"
            rules={[{ required: true, message: 'Please enter passport number' }]}
          >
            <Input placeholder="e.g., AB1234567" />
          </Form.Item>
        );
      case 'ip':
        return (
          <Form.Item
            name="ip_address"
            label="IP Address"
            rules={[{ required: true, message: 'Please enter IP address' }]}
          >
            <Input placeholder="e.g., 192.168.1.100" />
          </Form.Item>
        );
      case 'mac':
        return (
          <Form.Item
            name="mac_address"
            label="MAC Address"
            rules={[{ required: true, message: 'Please enter MAC address' }]}
          >
            <Input placeholder="e.g., AA:BB:CC:DD:EE:FF" />
          </Form.Item>
        );
      case 'date_range':
        return (
          <Form.Item
            name="dateRange"
            label="Date Range"
            rules={[{ required: true, message: 'Please select date range' }]}
          >
            <RangePicker
              showTime
              format="YYYY-MM-DD HH:mm:ss"
              style={{ width: '100%' }}
            />
          </Form.Item>
        );
      default:
        return null;
    }
  };

  const columns = [
    {
      title: 'User Information',
      key: 'user',
      width: 200,
      render: (_, record) => (
        <Space direction="vertical" size="small">
          <div><strong>{record.full_name || 'N/A'}</strong></div>
          <div style={{ fontSize: '12px' }}>
            <strong>Mobile:</strong> {record.mobile || 'N/A'}
          </div>
          <div style={{ fontSize: '12px', color: '#666' }}>
            <strong>ID:</strong> {record.cnic || record.passport || 'N/A'}
          </div>
        </Space>
      ),
    },
    {
      title: 'Session Times',
      key: 'session',
      width: 180,
      render: (_, record) => (
        <Space direction="vertical" size="small">
          <div style={{ fontSize: '12px' }}>
            <strong>Login:</strong><br/>
            {record.login_time
              ? dayjs(record.login_time).format('YYYY-MM-DD HH:mm:ss')
              : 'N/A'}
          </div>
          <div style={{ fontSize: '12px' }}>
            <strong>Logout:</strong><br/>
            {record.logout_time
              ? dayjs(record.logout_time).format('YYYY-MM-DD HH:mm:ss')
              : 'Active'}
          </div>
          {record.session_duration && (
            <Tag color="blue" style={{ fontSize: '11px' }}>
              {Math.floor(record.session_duration / 60)}m{' '}
              {record.session_duration % 60}s
            </Tag>
          )}
        </Space>
      ),
    },
    {
      title: 'Source Information',
      key: 'source',
      width: 180,
      render: (_, record) => (
        <Space direction="vertical" size="small">
          <div style={{ fontSize: '12px' }}>
            <strong>MAC:</strong><br/>
            {record.mac_address || 'N/A'}
          </div>
          <div style={{ fontSize: '12px' }}>
            <strong>IP:</strong> {record.source_ip}<br/>
            <strong>Port:</strong> {record.source_port}
          </div>
        </Space>
      ),
    },
    {
      title: 'NAT Translation',
      key: 'nat',
      width: 150,
      render: (_, record) => (
        <Space direction="vertical" size="small">
          {record.translated_ip ? (
            <>
              <div style={{ fontSize: '12px' }}>
                <strong>IP:</strong> {record.translated_ip}
              </div>
              <div style={{ fontSize: '12px' }}>
                <strong>Port:</strong> {record.translated_port || 'N/A'}
              </div>
            </>
          ) : (
            <div style={{ fontSize: '12px', color: '#999' }}>No NAT</div>
          )}
        </Space>
      ),
    },
    {
      title: 'Destination',
      key: 'destination',
      width: 180,
      render: (_, record) => (
        <Space direction="vertical" size="small">
          <div style={{ fontSize: '12px' }}>
            <strong>IP:</strong> {record.destination_ip}<br/>
            <strong>Port:</strong> {record.destination_port}
          </div>
          {record.url && (
            <Tooltip title={record.url}>
              <div
                style={{
                  fontSize: '11px',
                  maxWidth: '160px',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                  color: '#1890ff',
                }}
              >
                {record.url}
              </div>
            </Tooltip>
          )}
        </Space>
      ),
    },
    {
      title: 'Protocol & Application',
      key: 'protocol',
      width: 180,
      render: (_, record) => (
        <Space direction="vertical" size="small">
          <div style={{ fontSize: '12px' }}>
            <strong>Protocol:</strong>{' '}
            <Tag color="green" style={{ fontSize: '11px' }}>
              {record.protocol || 'N/A'}
            </Tag>
          </div>
          <div style={{ fontSize: '12px' }}>
            <strong>Service:</strong>{' '}
            <Tag color="blue" style={{ fontSize: '11px' }}>
              {record.service || 'N/A'}
            </Tag>
          </div>
          <div style={{ fontSize: '12px' }}>
            <strong>Application:</strong>{' '}
            <Tag color="orange" style={{ fontSize: '11px' }}>
              {record.app_name || 'N/A'}
            </Tag>
          </div>
        </Space>
      ),
    },
    {
      title: 'Data Consumption',
      key: 'data',
      width: 140,
      render: (_, record) => (
        <Space direction="vertical" size="small">
          <div style={{ fontSize: '12px' }}>
            <strong>Total:</strong><br/>
            {(record.data_consumption / (1024 * 1024)).toFixed(2)} MB
          </div>
          <div style={{ fontSize: '11px', color: '#666' }}>
            {record.log_timestamp
              ? dayjs(record.log_timestamp).format('HH:mm:ss')
              : ''}
          </div>
        </Space>
      ),
    },
  ];

  return (
    <div>
      {/* Statistics Cards */}
      {stats && (
        <Row gutter={16} style={{ marginBottom: 24 }}>
          <Col span={6}>
            <Card>
              <Statistic
                title="Total Firewall Logs"
                value={stats.total_firewall_logs}
                prefix={<DatabaseOutlined />}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="Logs with User Correlation"
                value={stats.logs_with_user_correlation}
                prefix={<FileTextOutlined />}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="Correlation Rate"
                value={stats.correlation_percentage}
                suffix="%"
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="Today's Logs"
                value={stats.todays_logs}
                prefix={<HistoryOutlined />}
              />
            </Card>
          </Col>
        </Row>
      )}

      {/* Syslog Status Card */}
      {syslogStatus && (
        <Card
          title="FortiGate Syslog Receiver Status"
          extra={
            <Button
              size="small"
              onClick={handleRestartSyslog}
              icon={<HistoryOutlined />}
            >
              Restart
            </Button>
          }
          style={{ marginBottom: 24 }}
        >
          <Row gutter={16}>
            <Col span={6}>
              <Statistic
                title="Status"
                value={syslogStatus.status}
                valueStyle={{
                  color: syslogStatus.running ? '#3f8600' : '#cf1322',
                }}
              />
            </Col>
            <Col span={6}>
              <Statistic title="Protocol" value={syslogStatus.protocol.toUpperCase()} />
            </Col>
            <Col span={6}>
              <Statistic title="Port" value={syslogStatus.port} />
            </Col>
            <Col span={6}>
              <Statistic
                title="Listen Address"
                value={syslogStatus.host === '0.0.0.0' ? 'All Interfaces' : syslogStatus.host}
              />
            </Col>
          </Row>
          <div style={{ marginTop: 16 }}>
            {syslogStatus.running ? (
              <Tag color="success">Real-time log collection ACTIVE</Tag>
            ) : (
              <Tag color="error">Real-time log collection STOPPED</Tag>
            )}
          </div>
        </Card>
      )}

      {/* Search Form */}
      <Card
        title="IPDR Search"
        extra={
          <Space>
            <Button
              icon={<UploadOutlined />}
              onClick={() => setImportModalVisible(true)}
            >
              Import CSV
            </Button>
            <Button
              type="primary"
              icon={<DownloadOutlined />}
              onClick={() => handleExport('csv')}
              disabled={!searchResults.length}
            >
              Export CSV
            </Button>
          </Space>
        }
        style={{ marginBottom: 24 }}
      >
        <Form form={form} layout="vertical" onFinish={handleSearch}>
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item label="Search Type" required>
                <Select
                  value={searchType}
                  onChange={(value) => {
                    setSearchType(value);
                    form.resetFields();
                  }}
                >
                  <Option value="mobile">Mobile Number</Option>
                  <Option value="cnic">CNIC Number</Option>
                  <Option value="passport">Passport Number</Option>
                  <Option value="ip">IP Address</Option>
                  <Option value="mac">MAC Address</Option>
                  <Option value="date_range">Date Range</Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={16}>{renderSearchFields()}</Col>
          </Row>

          <Form.Item>
            <Button
              type="primary"
              htmlType="submit"
              icon={<SearchOutlined />}
              loading={loading}
            >
              Search
            </Button>
          </Form.Item>
        </Form>
      </Card>

      {/* Results Table */}
      <Card title={`Search Results (${pagination.total} records)`}>
        <Table
          columns={columns}
          dataSource={searchResults}
          loading={loading}
          rowKey={(record) => `${record.source_ip}-${record.log_timestamp}`}
          pagination={pagination}
          onChange={handleTableChange}
          scroll={{ x: 1600, y: 600 }}
          size="small"
        />
      </Card>

      {/* Import Modal */}
      <Modal
        title="Import Firewall CSV Logs"
        open={importModalVisible}
        onCancel={() => setImportModalVisible(false)}
        footer={null}
      >
        <Space direction="vertical" style={{ width: '100%' }} size="large">
          <div>
            <h4>Supported Format:</h4>
            <ul>
              <li>FortiGate firewall log CSV format</li>
              <li>File must include headers</li>
              <li>Maximum file size: 100MB</li>
            </ul>
          </div>

          <Upload.Dragger
            name="file"
            accept=".csv"
            beforeUpload={handleCSVImport}
            showUploadList={false}
          >
            <p className="ant-upload-drag-icon">
              <UploadOutlined />
            </p>
            <p className="ant-upload-text">
              Click or drag CSV file to this area to upload
            </p>
            <p className="ant-upload-hint">
              Support for FortiGate log CSV format
            </p>
          </Upload.Dragger>

          {importJobs.length > 0 && (
            <div>
              <h4>Recent Import Jobs:</h4>
              {importJobs.slice(0, 5).map((job) => (
                <Descriptions key={job.id} bordered size="small" column={1}>
                  <Descriptions.Item label="File">
                    {job.filename}
                  </Descriptions.Item>
                  <Descriptions.Item label="Status">
                    <Tag
                      color={
                        job.status === 'completed'
                          ? 'success'
                          : job.status === 'failed'
                          ? 'error'
                          : 'processing'
                      }
                    >
                      {job.status.toUpperCase()}
                    </Tag>
                  </Descriptions.Item>
                  <Descriptions.Item label="Progress">
                    {job.imported_rows} / {job.total_rows || 0} rows imported
                    {job.failed_rows > 0 && ` (${job.failed_rows} failed)`}
                  </Descriptions.Item>
                  <Descriptions.Item label="Time">
                    {job.started_at
                      ? dayjs(job.started_at).format('YYYY-MM-DD HH:mm:ss')
                      : 'N/A'}
                  </Descriptions.Item>
                </Descriptions>
              ))}
            </div>
          )}
        </Space>
      </Modal>
    </div>
  );
};

export default IPDRReports;
