import { useState, useEffect, useRef } from 'react';
import { getActiveAds, trackAdEvent } from '../services/api';

function AdDisplay({ portalDesign, userData, onComplete, onSkip }) {
  const [ads, setAds] = useState([]);
  const [currentAdIndex, setCurrentAdIndex] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [canSkip, setCanSkip] = useState(false);
  const [timeRemaining, setTimeRemaining] = useState(0);
  const videoRef = useRef(null);

  useEffect(() => {
    loadAds();
  }, []);

  const loadAds = async () => {
    try {
      setLoading(true);
      const adsData = await getActiveAds();
      
      if (!adsData || adsData.length === 0) {
        // No ads, skip to login
        onComplete();
        return;
      }

      setAds(adsData);
      setError('');
      
      // Track first ad view
      if (adsData[0]) {
        await trackAdEvent(adsData[0].id, 'view', {
          user_id: userData?.id,
          mobile: userData?.mobile,
        });
        
        // Set skip timer
        const skipAfter = adsData[0].skip_after_seconds || 5;
        setTimeRemaining(skipAfter);
        setCanSkip(false);
      }
    } catch (err) {
      console.error('Failed to load ads:', err);
      setError('Failed to load advertisements');
      // Skip to login on error
      setTimeout(onComplete, 2000);
    } finally {
      setLoading(false);
    }
  };

  // Timer for skip button
  useEffect(() => {
    if (timeRemaining > 0) {
      const timer = setTimeout(() => {
        setTimeRemaining(timeRemaining - 1);
      }, 1000);
      return () => clearTimeout(timer);
    } else if (timeRemaining === 0 && ads.length > 0) {
      setCanSkip(true);
    }
  }, [timeRemaining, ads]);

  // Auto-advance for images
  useEffect(() => {
    if (ads.length === 0 || currentAdIndex >= ads.length) return;

    const currentAd = ads[currentAdIndex];
    
    if (currentAd.ad_type === 'image') {
      const duration = currentAd.display_duration * 1000;
      const timer = setTimeout(() => {
        handleNextAd();
      }, duration);
      return () => clearTimeout(timer);
    }
  }, [currentAdIndex, ads]);

  const handleNextAd = async () => {
    const currentAd = ads[currentAdIndex];
    
    // Track completion
    await trackAdEvent(currentAd.id, 'complete', {
      user_id: userData?.id,
      mobile: userData?.mobile,
    });

    if (currentAdIndex < ads.length - 1) {
      // Next ad
      const nextIndex = currentAdIndex + 1;
      setCurrentAdIndex(nextIndex);
      setCanSkip(false);
      
      const nextAd = ads[nextIndex];
      const skipAfter = nextAd.skip_after_seconds || 5;
      setTimeRemaining(skipAfter);
      
      // Track next ad view
      await trackAdEvent(nextAd.id, 'view', {
        user_id: userData?.id,
        mobile: userData?.mobile,
      });
    } else {
      // All ads done
      onComplete();
    }
  };

  const handleSkipAd = async () => {
    if (!canSkip) return;

    const currentAd = ads[currentAdIndex];
    
    // Track skip
    await trackAdEvent(currentAd.id, 'skip', {
      user_id: userData?.id,
      mobile: userData?.mobile,
    });

    handleNextAd();
  };

  const handleAdClick = async () => {
    const currentAd = ads[currentAdIndex];
    
    // Track click
    await trackAdEvent(currentAd.id, 'click', {
      user_id: userData?.id,
      mobile: userData?.mobile,
    });

    // Open link if available
    if (currentAd.link_url) {
      window.open(currentAd.link_url, '_blank');
    }
  };

  const handleVideoEnd = () => {
    handleNextAd();
  };

  if (loading) {
    return (
      <div className="portal-body">
        <div className="loading">
          <div className="spinner"></div>
          <p>Loading advertisements...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="portal-body">
        <div className="message message-error">{error}</div>
        <button className="btn btn-primary" onClick={onSkip}>
          Continue to Login
        </button>
      </div>
    );
  }

  if (ads.length === 0) {
    return null;
  }

  const currentAd = ads[currentAdIndex];
  
  // Check if all ads allow skipping
  const allAdsSkippable = ads.every(ad => ad.enable_skip);

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      width: '100vw',
      height: '100vh',
      backgroundColor: '#000',
      zIndex: 9999,
      display: 'flex',
      flexDirection: 'column',
      justifyContent: 'center',
      alignItems: 'center'
    }}>
      {/* Ad Counter & Title */}
      <div style={{
        position: 'absolute',
        top: 20,
        left: '50%',
        transform: 'translateX(-50%)',
        textAlign: 'center',
        color: 'white',
        zIndex: 10
      }}>
        <h2 style={{ fontSize: '18px', marginBottom: '5px' }}>
          Advertisement {currentAdIndex + 1} of {ads.length}
        </h2>
        <p style={{ fontSize: '14px', opacity: 0.8 }}>
          {currentAd.enable_skip 
            ? 'Please watch or skip to continue' 
            : 'Please watch this advertisement to continue'}
        </p>
      </div>

      {/* Ad Content - Full Screen */}
      <div style={{
        width: '100%',
        height: '100%',
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        position: 'relative'
      }}>
        {currentAd.ad_type === 'image' && (
          <img
            src={currentAd.file_path}
            alt={currentAd.title}
            onClick={handleAdClick}
            style={{
              maxWidth: '100%',
              maxHeight: '100%',
              objectFit: 'contain',
              cursor: currentAd.link_url ? 'pointer' : 'default'
            }}
          />
        )}

        {currentAd.ad_type === 'video' && (
          <video
            ref={videoRef}
            src={currentAd.file_path}
            autoPlay
            onEnded={handleVideoEnd}
            onClick={handleAdClick}
            style={{
              maxWidth: '100%',
              maxHeight: '100%',
              objectFit: 'contain',
              cursor: currentAd.link_url ? 'pointer' : 'default'
            }}
          />
        )}
      </div>

      {/* Skip Buttons - Outside Ad Content */}
      <div style={{
        position: 'absolute',
        bottom: 30,
        left: '50%',
        transform: 'translateX(-50%)',
        display: 'flex',
        flexDirection: 'column',
        gap: '15px',
        alignItems: 'center',
        zIndex: 10
      }}>
        {/* Individual Ad Skip Button */}
        {currentAd.enable_skip && (
          <button
            onClick={handleSkipAd}
            disabled={!canSkip}
            style={{
              padding: '12px 30px',
              backgroundColor: canSkip ? 'rgba(255, 255, 255, 0.9)' : 'rgba(255, 255, 255, 0.3)',
              color: canSkip ? '#000' : '#666',
              border: 'none',
              borderRadius: '25px',
              fontSize: '16px',
              fontWeight: '500',
              cursor: canSkip ? 'pointer' : 'not-allowed',
              transition: 'all 0.3s',
              minWidth: '150px'
            }}
          >
            {canSkip ? 'Skip Ad ›' : `Skip in ${timeRemaining}s`}
          </button>
        )}

        {/* Skip All Ads Button */}
        {allAdsSkippable && (
          <button
            onClick={onSkip}
            style={{
              padding: '10px 25px',
              backgroundColor: 'transparent',
              color: 'rgba(255, 255, 255, 0.7)',
              border: '1px solid rgba(255, 255, 255, 0.5)',
              borderRadius: '25px',
              fontSize: '14px',
              cursor: 'pointer',
              transition: 'all 0.3s',
              ':hover': {
                backgroundColor: 'rgba(255, 255, 255, 0.1)'
              }
            }}
            onMouseEnter={(e) => e.target.style.backgroundColor = 'rgba(255, 255, 255, 0.1)'}
            onMouseLeave={(e) => e.target.style.backgroundColor = 'transparent'}
          >
            Skip All Ads & Continue to Login
          </button>
        )}
      </div>

      {/* Ad Description (if exists) */}
      {currentAd.description && (
        <div style={{
          position: 'absolute',
          bottom: allAdsSkippable ? '140px' : '100px',
          left: '50%',
          transform: 'translateX(-50%)',
          color: 'rgba(255, 255, 255, 0.9)',
          fontSize: '14px',
          textAlign: 'center',
          maxWidth: '80%',
          padding: '10px 20px',
          backgroundColor: 'rgba(0, 0, 0, 0.5)',
          borderRadius: '8px'
        }}>
          {currentAd.description}
        </div>
      )}
    </div>
  );
}

export default AdDisplay;
