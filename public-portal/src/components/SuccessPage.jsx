import { useState, useEffect } from 'react';
import { authorizeWiFi } from '../services/api';

function SuccessPage({ portalDesign, userData }) {
  const [authorizing, setAuthorizing] = useState(true);
  const [authorized, setAuthorized] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    handleAuthorization();
  }, []);

  const handleAuthorization = async () => {
    try {
      setAuthorizing(true);
      
      // Get MAC address from URL params (captive portal should pass this)
      const urlParams = new URLSearchParams(window.location.search);
      const macAddress = urlParams.get('mac') || urlParams.get('client_mac') || urlParams.get('clientMac') || 'AA:BB:CC:DD:EE:FF'; // Fallback for testing
      const apMac = urlParams.get('ap_mac') || urlParams.get('apMac') || '00:00:00:00:00:01'; // Test AP MAC
      const ssid = urlParams.get('ssid') || urlParams.get('ssidName') || 'NTC-Public-WiFi'; // Test SSID

      console.log('Authorization params:', { macAddress, apMac, ssid, userData });

      // Authorize WiFi access
      await authorizeWiFi({
        user_id: userData?.id,
        mobile: userData?.mobile,
        mac_address: macAddress,
        ap_mac: apMac,
        ssid: ssid,
      });

      setAuthorized(true);
      setError('');

      // Redirect after 3 seconds
      setTimeout(() => {
        // Try to redirect to original URL
        const redirectUrl = urlParams.get('url') || 'http://www.google.com';
        window.location.href = redirectUrl;
      }, 3000);
    } catch (err) {
      console.error('Authorization failed:', err);
      setError('Failed to authorize WiFi access. Please try again or contact support.');
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
          </div>
        )}

        {!authorizing && authorized && (
          <>
            <div className="message message-success">
              ✓ You are now connected to WiFi!
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
              <p style={{ color: '#666' }}>Redirecting you to the internet...</p>
            </div>
            <div style={{ textAlign: 'center', fontSize: '13px', color: '#999' }}>
              <p>Session Details:</p>
              <p>Mobile: {userData?.mobile}</p>
              <p>Time Limit: 1 hour</p>
            </div>
          </>
        )}

        {!authorizing && error && (
          <>
            <div className="message message-error">{error}</div>
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
