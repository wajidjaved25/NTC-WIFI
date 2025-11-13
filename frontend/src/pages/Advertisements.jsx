import React, { useState, useEffect } from 'react';
import { Button, message, Modal, Tabs } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import AdUpload from '../components/Ads/AdUpload';
import AdsList from '../components/Ads/AdsList';
import api from '../services/api';

const Advertisements = () => {
  const [loading, setLoading] = useState(false);
  const [ads, setAds] = useState([]);
  const [uploadVisible, setUploadVisible] = useState(false);
  const [editingAd, setEditingAd] = useState(null);

  useEffect(() => {
    fetchAds();
  }, []);

  const fetchAds = async () => {
    setLoading(true);
    try {
      const response = await api.get('/ads');
      console.log('Ads response:', response.data);
      // Backend returns array directly, not wrapped in {ads: [...]}
      const adsData = Array.isArray(response.data) ? response.data : [];
      // Sort by display_order
      const sortedAds = adsData.sort((a, b) => a.display_order - b.display_order);
      setAds(sortedAds);
    } catch (error) {
      console.error('Failed to fetch ads:', error);
      message.error('Failed to load advertisements');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async (formData) => {
    try {
      if (editingAd) {
        // Update existing ad - backend uses PATCH method
        await api.patch(`/ads/${editingAd.id}`, formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
        });
        message.success('Advertisement updated successfully!');
      } else {
        // Create new ad
        await api.post('/ads', formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
        });
        message.success('Advertisement created successfully!');
      }
      
      setUploadVisible(false);
      setEditingAd(null);
      fetchAds();
    } catch (error) {
      console.error('Failed to save ad:', error);
      message.error('Failed to save advertisement: ' + (error.response?.data?.detail || 'Unknown error'));
      throw error;
    }
  };

  const handleEdit = (ad) => {
    setEditingAd(ad);
    setUploadVisible(true);
  };

  const handleDelete = async (adId) => {
    try {
      await api.delete(`/ads/${adId}`);
      message.success('Advertisement deleted successfully!');
      fetchAds();
    } catch (error) {
      console.error('Failed to delete ad:', error);
      message.error('Failed to delete advertisement');
    }
  };

  const handleToggle = async (adId, isActive) => {
    try {
      // Backend toggle endpoint doesn't need body - it just toggles the state
      await api.post(`/ads/${adId}/toggle`);
      message.success(`Advertisement ${isActive ? 'activated' : 'deactivated'}`);
      fetchAds();
    } catch (error) {
      console.error('Failed to toggle ad:', error);
      message.error('Failed to update advertisement status');
    }
  };

  const handleReorder = async (reorderedAds) => {
    try {
      // Update local state immediately for smooth UX
      setAds(reorderedAds);
      
      // Send new order to backend
      const orderData = reorderedAds.map((ad, index) => ({
        id: ad.id,
        display_order: index,
      }));
      
      await api.post('/ads/reorder', { ads: orderData });
      message.success('Ad order updated successfully!');
    } catch (error) {
      console.error('Failed to reorder ads:', error);
      message.error('Failed to update ad order');
      // Revert on error
      fetchAds();
    }
  };

  const handleCancel = () => {
    setUploadVisible(false);
    setEditingAd(null);
  };

  const activeAds = ads.filter(ad => ad.is_active);
  const inactiveAds = ads.filter(ad => !ad.is_active);

  return (
    <div className="advertisements">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <div>
          <h2>Advertisement Management</h2>
          <p style={{ color: '#666', margin: 0 }}>
            Upload and manage advertisements for the WiFi portal.
          </p>
        </div>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={() => setUploadVisible(true)}
        >
          Add Advertisement
        </Button>
      </div>

      <Tabs
        defaultActiveKey="active"
        items={[
          {
            key: 'active',
            label: `Active Ads (${activeAds.length})`,
            children: (
              <AdsList
                ads={activeAds}
                loading={loading}
                onEdit={handleEdit}
                onDelete={handleDelete}
                onToggle={handleToggle}
                onReorder={handleReorder}
              />
            ),
          },
          {
            key: 'inactive',
            label: `Inactive Ads (${inactiveAds.length})`,
            children: (
              <AdsList
                ads={inactiveAds}
                loading={loading}
                onEdit={handleEdit}
                onDelete={handleDelete}
                onToggle={handleToggle}
                onReorder={handleReorder}
              />
            ),
          },
          {
            key: 'all',
            label: `All Ads (${ads.length})`,
            children: (
              <AdsList
                ads={ads}
                loading={loading}
                onEdit={handleEdit}
                onDelete={handleDelete}
                onToggle={handleToggle}
                onReorder={handleReorder}
              />
            ),
          },
        ]}
      />

      {/* Upload/Edit Modal */}
      <Modal
        title={editingAd ? 'Edit Advertisement' : 'Add New Advertisement'}
        open={uploadVisible}
        onCancel={handleCancel}
        footer={null}
        width={800}
        destroyOnClose
      >
        <AdUpload
          initialData={editingAd}
          onSave={handleSave}
          onCancel={handleCancel}
          loading={false}
        />
      </Modal>
    </div>
  );
};

export default Advertisements;
