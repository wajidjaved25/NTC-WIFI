import React, { useState, useEffect } from 'react';
import { message } from 'antd';
import PortalDesignEditor from '../components/PortalDesign/PortalDesignEditor';
import LivePreview from '../components/PortalDesign/LivePreview';
import api from '../services/api';

const PortalDesign = () => {
  const [loading, setLoading] = useState(false);
  const [design, setDesign] = useState(null);
  const [previewVisible, setPreviewVisible] = useState(false);
  const [previewData, setPreviewData] = useState(null);

  useEffect(() => {
    fetchDesign();
  }, []);

  const fetchDesign = async () => {
    setLoading(true);
    try {
      const response = await api.get('/portal/design');
      setDesign(response.data);
    } catch (error) {
      console.error('Failed to fetch design:', error);
      message.error('Failed to load portal design');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async (formData) => {
    setLoading(true);
    try {
      let response;
      
      // Extract files from FormData
      const logoFile = formData.get('logo');
      const backgroundFile = formData.get('background');
      
      // Convert FormData to JSON object
      const jsonData = {};
      for (let [key, value] of formData.entries()) {
        if (key !== 'logo' && key !== 'background') {
          // Convert string booleans to actual booleans
          if (value === 'true') {
            jsonData[key] = true;
          } else if (value === 'false') {
            jsonData[key] = false;
          } else {
            jsonData[key] = value;
          }
        }
      }
      
      console.log('Sending to API:', jsonData);
      
      if (design && design.id) {
        // Upload files FIRST if provided (they may set show_logo/show_background to True)
        if (logoFile) {
          const logoFormData = new FormData();
          logoFormData.append('file', logoFile);
          await api.post(`/portal/designs/${design.id}/upload-logo`, logoFormData, {
            headers: { 'Content-Type': 'multipart/form-data' },
          });
        }
        
        if (backgroundFile) {
          const bgFormData = new FormData();
          bgFormData.append('file', backgroundFile);
          await api.post(`/portal/designs/${design.id}/upload-background`, bgFormData, {
            headers: { 'Content-Type': 'multipart/form-data' },
          });
        }
        
        // THEN update design settings (this will override any auto-enables from file uploads)
        response = await api.patch(`/portal/designs/${design.id}`, jsonData);
        console.log('API response:', response.data);
      } else {
        // Create new design
        response = await api.post('/portal/designs', jsonData);
        
        // Upload files for new design
        if (logoFile && response.data.id) {
          const logoFormData = new FormData();
          logoFormData.append('file', logoFile);
          await api.post(`/portal/designs/${response.data.id}/upload-logo`, logoFormData, {
            headers: { 'Content-Type': 'multipart/form-data' },
          });
        }
        
        if (backgroundFile && response.data.id) {
          const bgFormData = new FormData();
          bgFormData.append('file', backgroundFile);
          await api.post(`/portal/designs/${response.data.id}/upload-background`, bgFormData, {
            headers: { 'Content-Type': 'multipart/form-data' },
          });
        }
      }
      
      // Refresh design data
      const updatedDesign = await api.get('/portal/design');
      console.log('Updated design from API:', updatedDesign.data);
      setDesign(updatedDesign.data);
      
      message.success('Portal design saved successfully!');
      return updatedDesign.data;
    } catch (error) {
      console.error('Failed to save design:', error);
      message.error('Failed to save portal design: ' + (error.response?.data?.detail || 'Unknown error'));
      throw error;
    } finally {
      setLoading(false);
    }
  };

  const handlePreview = (data) => {
    setPreviewData(data);
    setPreviewVisible(true);
  };

  return (
    <div className="portal-design">
      <h2>Portal Design</h2>
      <p style={{ marginBottom: 24, color: '#666' }}>
        Customize the look and feel of your WiFi portal.
      </p>

      <PortalDesignEditor
        initialData={design}
        onSave={handleSave}
        onPreview={handlePreview}
        loading={loading}
      />

      <LivePreview
        visible={previewVisible}
        onClose={() => setPreviewVisible(false)}
        design={previewData}
      />
    </div>
  );
};

export default PortalDesign;
