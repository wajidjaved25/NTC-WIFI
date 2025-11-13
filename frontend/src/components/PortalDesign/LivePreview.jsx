import React from 'react';
import { Modal, Card } from 'antd';
import './LivePreview.css';

const LivePreview = ({ visible, onClose, design }) => {
  if (!design) return null;

  const previewStyle = {
    backgroundColor: design.background_color || '#f0f2f5',
    backgroundImage: design.background_image ? `url(${design.background_image})` : 'none',
    backgroundSize: 'cover',
    backgroundPosition: 'center',
    minHeight: '600px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    color: design.text_color || '#000000',
  };

  const cardStyle = {
    backgroundColor: design.secondary_color || '#ffffff',
    maxWidth: design.layout_type === 'fullscreen' ? '100%' : '500px',
    boxShadow: '0 4px 12px rgba(0, 0, 0, 0.15)',
  };

  const buttonStyle = {
    backgroundColor: design.primary_color || '#1890ff',
    color: design.secondary_color || '#ffffff',
    border: 'none',
    padding: '12px 24px',
    borderRadius: '4px',
    fontSize: '16px',
    cursor: 'pointer',
    marginTop: '16px',
  };

  const accentStyle = {
    color: design.accent_color || '#52c41a',
  };

  return (
    <Modal
      title="Portal Preview"
      open={visible}
      onCancel={onClose}
      footer={null}
      width="90%"
      style={{ top: 20 }}
      bodyStyle={{ padding: 0 }}
    >
      <div className="live-preview" style={previewStyle}>
        <Card style={cardStyle}>
          {/* Logo */}
          {design.logo_path && (
            <div style={{ textAlign: 'center', marginBottom: '24px' }}>
              <img
                src={design.logo_path}
                alt="Logo"
                style={{ maxWidth: '200px', maxHeight: '80px' }}
              />
            </div>
          )}

          {/* Welcome Title */}
          <h1 style={{ 
            textAlign: 'center', 
            color: design.primary_color || '#1890ff',
            fontSize: '28px',
            marginBottom: '16px',
          }}>
            {design.welcome_title || 'Welcome to Free WiFi'}
          </h1>

          {/* Welcome Text */}
          {design.welcome_text && (
            <div
              className="preview-content"
              style={{ marginBottom: '24px', textAlign: 'center' }}
              dangerouslySetInnerHTML={{ __html: design.welcome_text }}
            />
          )}

          {/* Sample Form */}
          <div style={{ marginTop: '24px' }}>
            <div style={{ marginBottom: '16px' }}>
              <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500' }}>
                Name
              </label>
              <input
                type="text"
                placeholder="Enter your name"
                style={{
                  width: '100%',
                  padding: '10px',
                  border: `1px solid ${design.primary_color || '#1890ff'}`,
                  borderRadius: '4px',
                }}
                disabled
              />
            </div>

            <div style={{ marginBottom: '16px' }}>
              <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500' }}>
                Mobile Number
              </label>
              <input
                type="tel"
                placeholder="Enter your mobile number"
                style={{
                  width: '100%',
                  padding: '10px',
                  border: `1px solid ${design.primary_color || '#1890ff'}`,
                  borderRadius: '4px',
                }}
                disabled
              />
            </div>

            <button style={buttonStyle} disabled>
              Get OTP
            </button>
          </div>

          {/* Terms */}
          {design.terms_text && (
            <div
              className="preview-terms"
              style={{ 
                marginTop: '24px', 
                fontSize: '12px',
                color: '#999',
                maxHeight: '150px',
                overflow: 'auto',
              }}
              dangerouslySetInnerHTML={{ __html: design.terms_text }}
            />
          )}

          {/* Footer */}
          {design.footer_text && (
            <div style={{ 
              marginTop: '24px', 
              textAlign: 'center',
              fontSize: '12px',
              color: '#999',
            }}>
              {design.footer_text}
            </div>
          )}

          {/* Accent Color Example */}
          <div style={{ 
            marginTop: '16px', 
            textAlign: 'center',
            ...accentStyle,
            fontSize: '14px',
          }}>
            ✓ Secure Connection
          </div>
        </Card>
      </div>

      {/* Apply Custom CSS */}
      {design.custom_css && (
        <style>{design.custom_css}</style>
      )}
    </Modal>
  );
};

export default LivePreview;
