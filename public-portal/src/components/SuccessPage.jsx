import { useState, useEffect } from 'react';

function SuccessPage({ portalDesign, userData }) {
  const [countdown, setCountdown] = useState(5);

  useEffect(() => {
    // Countdown timer
    const timer = setInterval(() => {
      setCountdown((prev) => {
        if (prev <= 1) {
          clearInterval(timer);
          redirectToOmada();
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, []);

  const redirectToOmada = () => {
    // Get URL params from Omada captive portal
    const urlParams = new URLSearchParams(window.location.search);
    
    // Omada captive portal URL - user needs to login here with mobile + CNIC
    // This redirects to Omada's built-in login page where RADIUS authentication happens
    const redirectUrl = urlParams.get('url') || 'http://192.168.3.1:8843/';
    
    window.location.href = redirectUrl;
  };

  const handleManualContinue = () => {
    redirectToOmada();
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
          Registration Complete!
        </h1>
      </div>

      <div className="portal-body">
        <div className="message message-success">
          ✓ Your account has been created successfully!
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
        </div>

        <div style={{ 
          background: '#f0f5ff', 
          border: '1px solid #adc6ff',
          borderRadius: '8px',
          padding: '20px', 
          marginBottom: '20px',
          textAlign: 'left'
        }}>
          <h4 style={{ marginBottom: '12px', color: '#1890ff' }}>📱 WiFi Login Instructions:</h4>
          <ol style={{ marginLeft: '20px', lineHeight: '1.8' }}>
            <li>You will be redirected to the WiFi login page</li>
            <li>Enter your credentials:
              <ul style={{ marginLeft: '20px', marginTop: '8px' }}>
                <li><strong>Username:</strong> {userData?.mobile}</li>
                <li><strong>Password:</strong> {userData?.id_type === 'cnic' ? userData?.cnic : userData?.passport}</li>
              </ul>
            </li>
            <li>Click "Login" to connect to WiFi</li>
            <li>Enjoy 1 hour of free internet access!</li>
          </ol>
        </div>

        <div style={{ textAlign: 'center', marginBottom: '20px' }}>
          <p style={{ fontSize: '16px', fontWeight: 'bold', color: '#1890ff' }}>
            Redirecting in {countdown} seconds...
          </p>
        </div>

        <button
          className="btn btn-primary"
          onClick={handleManualContinue}
          style={{ background: portalDesign?.primary_color }}
        >
          Continue to WiFi Login
        </button>
      </div>
    </>
  );
}

export default SuccessPage;
