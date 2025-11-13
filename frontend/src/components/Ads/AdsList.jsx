import React, { useState } from 'react';
import {
  List,
  Card,
  Tag,
  Space,
  Button,
  Switch,
  Popconfirm,
  Image,
  Typography,
  Row,
  Col,
  Statistic,
  Modal,
  message,
} from 'antd';
import {
  EditOutlined,
  DeleteOutlined,
  EyeOutlined,
  PlayCircleOutlined,
  FileImageOutlined,
  DownloadOutlined,
  DragOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import { DragDropContext, Droppable, Draggable } from 'react-beautiful-dnd';

const { Text, Title } = Typography;

const AdsList = ({ ads, loading, onEdit, onDelete, onToggle, onReorder }) => {
  const [previewVisible, setPreviewVisible] = useState(false);
  const [previewAd, setPreviewAd] = useState(null);

  const handlePreview = (ad) => {
    setPreviewAd(ad);
    setPreviewVisible(true);
  };

  const handleDragEnd = (result) => {
    if (!result.destination) return;

    const items = Array.from(ads);
    const [reorderedItem] = items.splice(result.source.index, 1);
    items.splice(result.destination.index, 0, reorderedItem);

    // Update display_order for all items
    const reordered = items.map((item, index) => ({
      ...item,
      display_order: index,
    }));

    onReorder(reordered);
  };

  const getAdTypeIcon = (type) => {
    switch (type) {
      case 'video':
        return <PlayCircleOutlined style={{ fontSize: 24, color: '#1890ff' }} />;
      case 'image':
        return <FileImageOutlined style={{ fontSize: 24, color: '#52c41a' }} />;
      case 'download':
        return <DownloadOutlined style={{ fontSize: 24, color: '#faad14' }} />;
      default:
        return null;
    }
  };

  const getStatusTag = (ad) => {
    if (!ad.is_active) {
      return <Tag color="default">Inactive</Tag>;
    }

    const now = dayjs();
    if (ad.start_date && dayjs(ad.start_date).isAfter(now)) {
      return <Tag color="orange">Scheduled</Tag>;
    }
    if (ad.end_date && dayjs(ad.end_date).isBefore(now)) {
      return <Tag color="red">Expired</Tag>;
    }
    return <Tag color="green">Active</Tag>;
  };

  const formatBytes = (bytes) => {
    if (!bytes) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${(bytes / Math.pow(k, i)).toFixed(2)} ${sizes[i]}`;
  };

  return (
    <>
      <DragDropContext onDragEnd={handleDragEnd}>
        <Droppable droppableId="ads-list">
          {(provided) => (
            <div
              {...provided.droppableProps}
              ref={provided.innerRef}
            >
              <List
                loading={loading}
                dataSource={ads}
                renderItem={(ad, index) => (
                  <Draggable
                    key={ad.id.toString()}
                    draggableId={ad.id.toString()}
                    index={index}
                  >
                    {(provided, snapshot) => (
                      <div
                        ref={provided.innerRef}
                        {...provided.draggableProps}
                        style={{
                          ...provided.draggableProps.style,
                          marginBottom: 16,
                        }}
                      >
                        <Card
                          className={snapshot.isDragging ? 'dragging' : ''}
                          style={{
                            backgroundColor: snapshot.isDragging ? '#f0f2f5' : 'white',
                          }}
                        >
                          <Row gutter={16} align="middle">
                            <Col flex="40px">
                              <div
                                {...provided.dragHandleProps}
                                style={{ cursor: 'grab', fontSize: 20 }}
                              >
                                <DragOutlined />
                              </div>
                            </Col>

                            <Col flex="80px">
                              {getAdTypeIcon(ad.ad_type)}
                            </Col>

                            <Col flex="auto">
                              <Space direction="vertical" size={4} style={{ width: '100%' }}>
                                <Space>
                                  <Title level={5} style={{ margin: 0 }}>
                                    {ad.title}
                                  </Title>
                                  {getStatusTag(ad)}
                                  <Tag color="blue">Order: {ad.display_order}</Tag>
                                </Space>

                                <Text type="secondary">{ad.description}</Text>

                                <Space size={16}>
                                  <Text>
                                    <strong>Type:</strong> {ad.ad_type}
                                  </Text>
                                  <Text>
                                    <strong>Duration:</strong> {ad.display_duration}s
                                  </Text>
                                  <Text>
                                    <strong>Size:</strong> {formatBytes(ad.file_size)}
                                  </Text>
                                  {ad.start_date && (
                                    <Text>
                                      <strong>Start:</strong> {dayjs(ad.start_date).format('YYYY-MM-DD')}
                                    </Text>
                                  )}
                                  {ad.end_date && (
                                    <Text>
                                      <strong>End:</strong> {dayjs(ad.end_date).format('YYYY-MM-DD')}
                                    </Text>
                                  )}
                                </Space>

                                <Space size={16}>
                                  <Statistic
                                    title="Views"
                                    value={ad.view_count}
                                    prefix={<EyeOutlined />}
                                    valueStyle={{ fontSize: 16 }}
                                  />
                                  <Statistic
                                    title="Clicks"
                                    value={ad.click_count}
                                    valueStyle={{ fontSize: 16 }}
                                  />
                                  <Statistic
                                    title="Skips"
                                    value={ad.skip_count}
                                    valueStyle={{ fontSize: 16 }}
                                  />
                                </Space>
                              </Space>
                            </Col>

                            <Col>
                              <Space direction="vertical" align="end">
                                <Switch
                                  checked={ad.is_active}
                                  onChange={(checked) => onToggle(ad.id, checked)}
                                  checkedChildren="ON"
                                  unCheckedChildren="OFF"
                                />

                                <Space>
                                  <Button
                                    icon={<EyeOutlined />}
                                    onClick={() => handlePreview(ad)}
                                    size="small"
                                  >
                                    Preview
                                  </Button>
                                  <Button
                                    icon={<EditOutlined />}
                                    onClick={() => onEdit(ad)}
                                    size="small"
                                  />
                                  <Popconfirm
                                    title="Delete this advertisement?"
                                    description="This action cannot be undone."
                                    onConfirm={() => onDelete(ad.id)}
                                    okText="Yes"
                                    cancelText="No"
                                  >
                                    <Button
                                      danger
                                      icon={<DeleteOutlined />}
                                      size="small"
                                    />
                                  </Popconfirm>
                                </Space>
                              </Space>
                            </Col>
                          </Row>
                        </Card>
                      </div>
                    )}
                  </Draggable>
                )}
              />
              {provided.placeholder}
            </div>
          )}
        </Droppable>
      </DragDropContext>

      {/* Preview Modal */}
      <Modal
        title={previewAd?.title}
        open={previewVisible}
        onCancel={() => setPreviewVisible(false)}
        footer={null}
        width={800}
      >
        {previewAd && (
          <div style={{ textAlign: 'center' }}>
            {previewAd.ad_type === 'image' && (
              <Image
                src={previewAd.file_path}
                alt={previewAd.title}
                style={{ maxWidth: '100%' }}
              />
            )}
            {previewAd.ad_type === 'video' && (
              <video
                controls
                style={{ maxWidth: '100%' }}
                src={previewAd.file_path}
              />
            )}
            {previewAd.ad_type === 'download' && (
              <div>
                <DownloadOutlined style={{ fontSize: 48, color: '#1890ff' }} />
                <p>
                  <a href={previewAd.file_path} download>
                    Download {previewAd.file_name}
                  </a>
                </p>
              </div>
            )}
            <p style={{ marginTop: 16 }}>{previewAd.description}</p>
          </div>
        )}
      </Modal>

      <style>{`
        .dragging {
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        }
      `}</style>
    </>
  );
};

export default AdsList;
