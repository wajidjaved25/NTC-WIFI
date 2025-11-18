import { useState, useEffect } from 'react';
import LoginForm from './components/LoginForm';
import AdDisplay from './components/AdDisplay';
import SuccessPage from './components/SuccessPage';
import { getPortalDesign } from './services/api';

function App() {
  const [step, setStep] = useState('ads'); // ads, login, success
  const [portalDesign, setPortalDesign] = useState(null);
  const [userData, setUserData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // CRITICAL: Capture and preserve Omada URL parameters
  const [omadaParams, setOmadaParams] = useState(null);

  // Load portal design from admin settings
  useEffect(() => {
    loadPortalDesign();
    
    // Capture URL parameters from Omada captive portal
    const urlParams = new URLSearchParams(window.location.search);
    const params = {
      mac: urlParams.get('mac') || urlParams.get('client_mac') || urlParams.get('clientMac'),
      ap_mac: urlParams.get('ap_mac') || urlParams.get('apMac'),
      ssid: urlParams.get('ssid') || urlParams.get('ssidName'),
      redirect_url: urlParams.get('url') || urlParams.get('redirect_url')
    };
    
    console.log('🔍 Captured Omada Parameters:', params);
    setOmadaParams(params);
  }, []);

  const loadPortalDesign = async () => {
    try {
      setLoading(true);
      const design = await getPortalDesign();
      setPortalDesign(design);
      setError(null);
    } catch (err) {
      console.error('Failed to load portal design:', err);
      setError('Failed to load portal configuration');
      // Use default design
      setPortalDesign(getDefaultDesign());
    } finally {
      setLoading(false);
    }
  };

  const getDefaultDesign = () => ({
    template_name: 'Default Portal',
    primary_color: '#1890ff',
    secondary_color: '#52c41a',
    background_color: '#ffffff',
    text_color: '#000000',
    font_family: 'Arial, sans-serif',
    welcome_title: 'Welcome to NTC Public WiFi',
    welcome_text: 'Please login to access free WiFi',
    terms_text: '<p>By using this service, you agree to our terms and conditions.</p>',
    footer_text: '© 2024 NTC. All rights reserved.',
    show_logo: true,
    show_background: false,
    enable_animations: true,
  });

  const handleLoginSuccess = (user) => {
    setUserData(user);
    setStep('success');
  };

  const handleAdsComplete = () => {
    setStep('login');
  };

  const handleSkipAds = () => {
    setStep('login');
  };

  // Apply portal design
  const getContainerStyle = () => {
    if (!portalDesign) return {};
    
    // IMPORTANT: Use background_color field for the container background
    // NOT secondary_color (which is for UI elements like headers)
    return {
      backgroundColor: portalDesign.background_color || '#ffffff',
      backgroundImage: portalDesign.show_background && portalDesign.background_image
        ? `url(${portalDesign.background_image})`
        : 'none',
      backgroundSize: 'cover',
      backgroundPosition: 'center',
      color: portalDesign.text_color || '#000000',
      fontFamily: portalDesign.font_family || 'Arial, sans-serif',
    };
  };

  if (loading) {
    return (
      <div className="portal-container" style={getContainerStyle()}>
        <div className="portal-content">
          <div className="loading">
            <div className="spinner"></div>
            <p>Loading portal...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="portal-container" style={getContainerStyle()}>
      <div className="portal-content">
        {error && (
          <div className="message message-error" style={{ margin: '20px' }}>
            {error}
          </div>
        )}

        {step === 'ads' && (
          <AdDisplay
            portalDesign={portalDesign}
            userData={userData}
            onComplete={handleAdsComplete}
            onSkip={handleSkipAds}
          />
        )}

        {step === 'login' && (
          <LoginForm
            portalDesign={portalDesign}
            onSuccess={handleLoginSuccess}
          />
        )}

        {step === 'success' && (
          <SuccessPage
            portalDesign={portalDesign}
            userData={userData}
            omadaParams={omadaParams}
          />
        )}

        {/* Footer */}
        <div 
          className="portal-footer"
          style={{ 
            background: '#001529',
            color: 'rgba(255, 255, 255, 0.85)',
            padding: '20px',
            marginTop: '20px'
          }}
        >
          <div 
            dangerouslySetInnerHTML={{ __html: portalDesign?.footer_text || '© 2024 NTC' }}
            style={{ marginBottom: '12px', fontSize: '13px' }}
          />
          <div style={{ 
            display: 'flex', 
            alignItems: 'center', 
            justifyContent: 'center',
            gap: '8px',
            fontSize: '12px',
            flexWrap: 'wrap'
          }}>
            <span>In collaboration with</span>
            <a 
              href="https://www.superapp.pk" 
              target="_blank" 
              rel="noopener noreferrer"
              style={{ display: 'inline-block', lineHeight: 0 }}
            >
              <img 
                src="/SuperApp-white-logo.png" 
                alt="SuperApp - The Digital Powerhouse" 
                style={{ height: '24px', width: 'auto', verticalAlign: 'middle' }}
                onError={(e) => { e.target.style.display = 'none'; }}
              />
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
