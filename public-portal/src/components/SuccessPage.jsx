import { useState, useEffect } from 'react';
import { authorizeWiFi } from '../services/api';

function SuccessPage({ portalDesign, userData, omadaParams }) {
  const [authorizing, setAuthorizing] = useState(true);
  const [authorized, setAuthorized] = useState(false);
  const [error, setError] = useState('');
  const [authData, setAuthData] = useState(null);

  useEffect(() => {
    handleAuthorization();
  }, []);

  const handleAuthorization = async () => {
    try {
      setAuthorizing(true);
      
      console.log('🔐 === WIFI AUTHORIZATION DEBUG ===');
      console.log('User Data:', userData);
      console.log('Omada Params (preserved):', omadaParams);
      console.log('===================================');

      // Use preserved parameters from App.jsx
      const macAddress = omadaParams?.mac;
      const apMac = omadaParams?.ap_mac;
      const ssid = omadaParams?.ssid;
      
      const finalMacAddress = macAddress || 'AA:BB:CC:DD:EE:FF';
      
      if (!macAddress) {
        console.warn('⚠️ No MAC address from Omada - using test MAC');
      }

      // Call backend to create RADIUS user and validate
      const result = await authorizeWiFi({
        user_id: userData?.id,
        mobile: userData?.mobile,
        mac_address: finalMacAddress,
        ap_mac: apMac,
        ssid: ssid,
      });

      setAuthorized(true);
      setAuthData(result);
      setError('');

      // For RADIUS Server + External Portal:
      // Redirect client back to Omada's RADIUS authentication
      // Omada will then authenticate with RADIUS server using the credentials
      
      setTimeout(() => {
        // Build Omada RADIUS login URL
        // The client needs to authenticate through Omada with RADIUS credentials
        const baseUrl = omadaParams?.redirect_url || result.redirect_url;
        
        // If we have the original Omada auth URL, redirect there
        // The client will need to enter credentials on Omada's form
        // OR we can try auto-login via URL parameters
        
        console.log('🔗 Redirecting to:', baseUrl);
        window.location.href = baseUrl || 'http://www.google.com';
      }, 3000);
      
    } catch (err) {
      console.error('Authorization failed:', err);
      setError(err.response?.data?.detail || err.message || 'Failed to authorize WiFi access');
      setAuthorized(false);
    } finally {
      setAuthorizing(false);
    }
  };

  return (
    <>
      <div className="portal-header">
        {portalDesign?.show_logo && portalDesign?.logo_path && (
          <img
            src={portalDesign.logo_path}
            alt="Logo"
            className="portal-logo"
          />
        )}
        <h1 className="portal-title" style={{ color: portalDesign?.primary_color }}>
          {authorizing ? 'Connecting...' : authorized ? 'Connected!' : 'Connection Failed'}
        </h1>
      </div>

      <div className="portal-body">
        {authorizing && (
          <div className="loading">
            <div className="spinner"></div>
            <p>Authorizing WiFi access...</p>
            <p style={{ fontSize: '13px', color: '#666', marginTop: '10px' }}>Please wait while we connect you</p>
          </div>
        )}

        {!authorizing && authorized && (
          <>
            <div className="message message-success">
              ✓ Registration Complete!
            </div>
            <div style={{ textAlign: 'center', padding: '20px 0' }}>
              <svg
                width="80"
                height="80"
                viewBox="0 0 80 80"
                fill="none"
                xmlns="http://www.w3.org/2000/svg"
                style={{ margin: '0 auto 20px' }}
              >
                <circle cx="40" cy="40" r="40" fill="#52c41a" fillOpacity="0.1" />
                <path
                  d="M25 40L35 50L55 30"
                  stroke="#52c41a"
                  strokeWidth="4"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
              <h3 style={{ marginBottom: '10px' }}>Welcome, {userData?.name}!</h3>
              <p style={{ color: '#666', marginBottom: '20px' }}>Your WiFi credentials are ready</p>
              
              {/* Show RADIUS credentials for Omada login */}
              <div style={{ 
                background: '#f0f9ff', 
                border: '1px solid #91d5ff',
                borderRadius: '8px',
                padding: '15px', 
                margin: '15px 0',
                textAlign: 'left'
              }}>
                <p style={{ fontWeight: 'bold', marginBottom: '10px', color: '#1890ff' }}>
                  🔐 Your WiFi Login Credentials:
                </p>
                <p style={{ margin: '5px 0' }}>
                  <strong>Username:</strong> {userData?.mobile}
                </p>
                <p style={{ margin: '5px 0' }}>
                  <strong>Password:</strong> Your CNIC/Passport number
                </p>
              </div>
              
              <p style={{ color: '#666', fontSize: '13px', marginTop: '15px' }}>
                Connecting you to WiFi...
              </p>
            </div>
            <div style={{ textAlign: 'center', fontSize: '13px', color: '#999' }}>
              <p>Session Duration: 1 hour</p>
            </div>
          </>
        )}

        {!authorizing && error && (
          <>
            <div className="message message-error">
              {error}
            </div>
            <div style={{ 
              background: '#fff7e6', 
              border: '1px solid="#ffd591',
              borderRadius: '8px',
              padding: '15px', 
              margin: '20px 0',
              textAlign: 'left',
              fontSize: '13px'
            }}>
              <strong>⚠️ Troubleshooting:</strong>
              <ul style={{ marginLeft: '20px', marginTop: '8px', lineHeight: '1.6' }}>
                <li>Make sure you're connected to the WiFi network</li>
                <li>Try refreshing the page</li>
                <li>Check that captive portal is enabled</li>
                <li>Contact support if issue persists</li>
              </ul>
            </div>
            <button
              className="btn btn-primary"
              onClick={handleAuthorization}
              style={{ background: portalDesign?.primary_color }}
            >
              Try Again
            </button>
          </>
        )}
      </div>
    </>
  );
}

export default SuccessPage;
