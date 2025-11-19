import { useState, useRef, useEffect } from 'react';
import { sendOTP, verifyOTP, registerUser } from '../services/api';
import TermsModal from './TermsModal';

function LoginForm({ portalDesign, onSuccess }) {
  const [step, setStep] = useState('info'); // info, otp
  const [formData, setFormData] = useState({
    name: '',
    mobile: '',
    id_type: 'cnic',
    cnic: '',
    passport: '',
    terms_accepted: false,
  });
  const [otp, setOtp] = useState(['', '', '', '', '', '']);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [timer, setTimer] = useState(0);
  const [showTerms, setShowTerms] = useState(false);
  const otpRefs = useRef([]);

  // Timer countdown
  useEffect(() => {
    if (timer > 0) {
      const interval = setInterval(() => {
        setTimer((prev) => prev - 1);
      }, 1000);
      return () => clearInterval(interval);
    }
  }, [timer]);

  const handleInputChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData({
      ...formData,
      [name]: type === 'checkbox' ? checked : value,
    });
    setError('');
  };

  const validateMobile = (mobile) => {
    const mobileRegex = /^(\+92|0)?3[0-9]{9}$/;
    return mobileRegex.test(mobile);
  };

  const validateCNIC = (cnic) => {
    const cnicRegex = /^[0-9]{5}-[0-9]{7}-[0-9]$/;
    return cnicRegex.test(cnic);
  };

  const handleSendOTP = async (e) => {
    e.preventDefault();

    // Validation
    if (!formData.name.trim()) {
      setError('Please enter your name');
      return;
    }

    if (!validateMobile(formData.mobile)) {
      setError('Please enter a valid mobile number (03XXXXXXXXX)');
      return;
    }

    if (formData.id_type === 'cnic') {
      if (!validateCNIC(formData.cnic)) {
        setError('Please enter a valid CNIC (XXXXX-XXXXXXX-X)');
        return;
      }
    } else {
      if (!formData.passport.trim()) {
        setError('Please enter your passport number');
        return;
      }
    }

    if (!formData.terms_accepted) {
      setError('Please accept the terms and conditions');
      return;
    }

    setLoading(true);
    setError('');

    try {
      await sendOTP(formData.mobile);
      setStep('otp');
      setTimer(120); // 2 minutes
      setError('');
      setSuccess('OTP sent successfully!');
      setTimeout(() => setSuccess(''), 3000);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to send OTP');
    } finally {
      setLoading(false);
    }
  };

  const handleOTPChange = (index, value) => {
    if (value.length > 1) {
      value = value[0];
    }

    if (!/^\d*$/.test(value)) {
      return;
    }

    const newOtp = [...otp];
    newOtp[index] = value;
    setOtp(newOtp);

    // Auto-focus next input
    if (value && index < 5) {
      otpRefs.current[index + 1]?.focus();
    }

    setError('');
  };

  const handleOTPKeyDown = (index, e) => {
    if (e.key === 'Backspace' && !otp[index] && index > 0) {
      otpRefs.current[index - 1]?.focus();
    }
  };

  const handleOTPPaste = (e) => {
    e.preventDefault();
    const pastedData = e.clipboardData.getData('text').replace(/\D/g, '').slice(0, 6);
    if (pastedData) {
      const newOtp = [...otp];
      for (let i = 0; i < pastedData.length; i++) {
        newOtp[i] = pastedData[i];
      }
      setOtp(newOtp);
      if (pastedData.length === 6) {
        otpRefs.current[5]?.focus();
      }
    }
  };

  const handleVerifyOTP = async (e) => {
    e.preventDefault();

    const otpCode = otp.join('');
    if (otpCode.length !== 6) {
      setError('Please enter complete OTP');
      return;
    }

    setLoading(true);
    setError('');

    try {
      // Verify OTP
      await verifyOTP(formData.mobile, otpCode);

      // Register user
      const userData = {
        name: formData.name,
        mobile: formData.mobile,
        id_type: formData.id_type,
        cnic: formData.id_type === 'cnic' ? formData.cnic : null,
        passport: formData.id_type === 'passport' ? formData.passport : null,
        terms_accepted: formData.terms_accepted,
      };

      const response = await registerUser(userData);
      onSuccess(response.user);
    } catch (err) {
      setError(err.response?.data?.detail || 'Invalid OTP');
    } finally {
      setLoading(false);
    }
  };

  const handleResendOTP = async () => {
    if (timer > 0) return;

    setLoading(true);
    setError('');

    try {
      await sendOTP(formData.mobile);
      setTimer(120);
      setOtp(['', '', '', '', '', '']);
      setSuccess('OTP resent successfully!');
      setTimeout(() => setSuccess(''), 3000);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to resend OTP');
    } finally {
      setLoading(false);
    }
  };

  const formatMobile = (mobile) => {
    mobile = mobile.replace(/\D/g, '');
    if (mobile.startsWith('+92')) {
      mobile = '0' + mobile.slice(3);
    }
    return mobile;
  };

  const formatCNIC = (cnic) => {
    cnic = cnic.replace(/\D/g, '');
    if (cnic.length > 5) {
      cnic = cnic.slice(0, 5) + '-' + cnic.slice(5);
    }
    if (cnic.length > 13) {
      cnic = cnic.slice(0, 13) + '-' + cnic.slice(13);
    }
    return cnic.slice(0, 15);
  };

  return (
    <>
      {/* Header with Logo */}
      <div className="portal-header animate-fade-in">
        {portalDesign?.show_logo && portalDesign?.logo_path && (
          <img
            src={portalDesign.logo_path}
            alt="Logo"
            className="portal-logo"
          />
        )}
        <h1 className="portal-title" style={{ color: portalDesign?.primary_color }}>
          {portalDesign?.welcome_title || 'Welcome to Free WiFi'}
        </h1>
        <p className="portal-subtitle">
          {portalDesign?.welcome_text || 'Connect in seconds'}
        </p>
      </div>

      {/* Progress Indicator */}
      <div className="progress-steps">
        <div className={`progress-step ${step === 'info' ? 'active' : 'completed'}`}>
          <div className="step-number">1</div>
          <span>Your Info</span>
        </div>
        <div className="progress-line"></div>
        <div className={`progress-step ${step === 'otp' ? 'active' : ''}`}>
          <div className="step-number">2</div>
          <span>Verify OTP</span>
        </div>
      </div>

      {/* Main Form Card */}
      <div className="form-card animate-slide-up">
        {/* Messages */}
        {error && (
          <div className="message message-error animate-shake">
            <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
            </svg>
            {error}
          </div>
        )}

        {success && (
          <div className="message message-success animate-fade-in">
            <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
            </svg>
            {success}
          </div>
        )}

        {/* Step 1: User Info */}
        {step === 'info' && (
          <form onSubmit={handleSendOTP} className="animate-fade-in">
            {/* Name Input */}
            <div className="form-group">
              <div className="input-wrapper">
                <span className="input-icon">
                  <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z" clipRule="evenodd" />
                  </svg>
                </span>
                <input
                  type="text"
                  name="name"
                  className="form-input with-icon"
                  value={formData.name}
                  onChange={handleInputChange}
                  placeholder="Full Name"
                  required
                />
              </div>
            </div>

            {/* Mobile Input */}
            <div className="form-group">
              <div className="input-wrapper">
                <span className="input-icon">
                  <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
                    <path d="M2 3a1 1 0 011-1h2.153a1 1 0 01.986.836l.74 4.435a1 1 0 01-.54 1.06l-1.548.773a11.037 11.037 0 006.105 6.105l.774-1.548a1 1 0 011.059-.54l4.435.74a1 1 0 01.836.986V17a1 1 0 01-1 1h-2C7.82 18 2 12.18 2 5V3z" />
                  </svg>
                </span>
                <input
                  type="tel"
                  name="mobile"
                  className="form-input with-icon"
                  value={formData.mobile}
                  onChange={(e) => {
                    const formatted = formatMobile(e.target.value);
                    setFormData({ ...formData, mobile: formatted });
                  }}
                  placeholder="03XXXXXXXXX"
                  maxLength="11"
                  required
                />
              </div>
            </div>

            {/* ID Type Toggle */}
            <div className="form-group">
              <div className="id-type-toggle">
                <button
                  type="button"
                  className={`toggle-btn ${formData.id_type === 'cnic' ? 'active' : ''}`}
                  onClick={() => setFormData({ ...formData, id_type: 'cnic' })}
                  style={formData.id_type === 'cnic' ? { background: portalDesign?.primary_color } : {}}
                >
                  CNIC
                </button>
                <button
                  type="button"
                  className={`toggle-btn ${formData.id_type === 'passport' ? 'active' : ''}`}
                  onClick={() => setFormData({ ...formData, id_type: 'passport' })}
                  style={formData.id_type === 'passport' ? { background: portalDesign?.primary_color } : {}}
                >
                  Passport
                </button>
              </div>
            </div>

            {/* CNIC/Passport Input */}
            {formData.id_type === 'cnic' ? (
              <div className="form-group">
                <div className="input-wrapper">
                  <span className="input-icon">
                    <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
                      <path fillRule="evenodd" d="M4 4a2 2 0 012-2h8a2 2 0 012 2v12a2 2 0 01-2 2H6a2 2 0 01-2-2V4zm3 1h6v4H7V5zm6 6H7v2h6v-2z" clipRule="evenodd" />
                    </svg>
                  </span>
                  <input
                    type="text"
                    name="cnic"
                    className="form-input with-icon"
                    value={formData.cnic}
                    onChange={(e) => {
                      const formatted = formatCNIC(e.target.value);
                      setFormData({ ...formData, cnic: formatted });
                    }}
                    placeholder="XXXXX-XXXXXXX-X"
                    maxLength="15"
                    required
                  />
                </div>
              </div>
            ) : (
              <div className="form-group">
                <div className="input-wrapper">
                  <span className="input-icon">
                    <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
                      <path fillRule="evenodd" d="M4 4a2 2 0 012-2h8a2 2 0 012 2v12a2 2 0 01-2 2H6a2 2 0 01-2-2V4zm3 1h6v4H7V5zm6 6H7v2h6v-2z" clipRule="evenodd" />
                    </svg>
                  </span>
                  <input
                    type="text"
                    name="passport"
                    className="form-input with-icon"
                    value={formData.passport}
                    onChange={handleInputChange}
                    placeholder="Passport Number"
                    required
                  />
                </div>
              </div>
            )}

            {/* Terms Checkbox */}
            <div className="form-group">
              <label className="checkbox-container">
                <input
                  type="checkbox"
                  name="terms_accepted"
                  checked={formData.terms_accepted}
                  onChange={handleInputChange}
                  required
                />
                <span className="checkmark"></span>
                <span className="checkbox-label">
                  I accept the{' '}
                  <a
                    href="#"
                    onClick={(e) => {
                      e.preventDefault();
                      setShowTerms(true);
                    }}
                    style={{ color: portalDesign?.primary_color }}
                  >
                    Terms & Conditions
                  </a>
                </span>
              </label>
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              className="btn btn-primary btn-block"
              disabled={loading}
              style={{ background: portalDesign?.primary_color }}
            >
              {loading ? (
                <span className="btn-loading">
                  <span className="spinner-small"></span>
                  Sending OTP...
                </span>
              ) : (
                <>
                  Get OTP
                  <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor" style={{ marginLeft: '8px' }}>
                    <path fillRule="evenodd" d="M10.293 3.293a1 1 0 011.414 0l6 6a1 1 0 010 1.414l-6 6a1 1 0 01-1.414-1.414L14.586 11H3a1 1 0 110-2h11.586l-4.293-4.293a1 1 0 010-1.414z" clipRule="evenodd" />
                  </svg>
                </>
              )}
            </button>
          </form>
        )}

        {/* Step 2: OTP Verification */}
        {step === 'otp' && (
          <form onSubmit={handleVerifyOTP} className="animate-fade-in">
            <div className="otp-info">
              <div className="otp-icon">
                <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
                  <circle cx="24" cy="24" r="24" fill={portalDesign?.primary_color || '#1890ff'} opacity="0.1"/>
                  <path d="M24 14v10l8 4" stroke={portalDesign?.primary_color || '#1890ff'} strokeWidth="2" strokeLinecap="round"/>
                </svg>
              </div>
              <p>Enter the 6-digit code sent to</p>
              <strong>{formData.mobile}</strong>
            </div>

            {/* OTP Input */}
            <div className="otp-container" onPaste={handleOTPPaste}>
              {otp.map((digit, index) => (
                <input
                  key={index}
                  ref={(el) => (otpRefs.current[index] = el)}
                  type="text"
                  inputMode="numeric"
                  className="otp-input"
                  value={digit}
                  onChange={(e) => handleOTPChange(index, e.target.value)}
                  onKeyDown={(e) => handleOTPKeyDown(index, e)}
                  maxLength="1"
                  style={{ 
                    borderColor: digit ? portalDesign?.primary_color : '#d9d9d9',
                    background: digit ? `${portalDesign?.primary_color}10` : '#fff'
                  }}
                />
              ))}
            </div>

            {/* Timer / Resend */}
            <div className="otp-actions">
              {timer > 0 ? (
                <div className="timer">
                  <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                    <path fillRule="evenodd" d="M8 14A6 6 0 108 2a6 6 0 000 12zm1-6V5a1 1 0 10-2 0v3.586l-1.707 1.707a1 1 0 001.414 1.414l2-2A1 1 0 009 8z" clipRule="evenodd" />
                  </svg>
                  Resend in {Math.floor(timer / 60)}:{(timer % 60).toString().padStart(2, '0')}
                </div>
              ) : (
                <button
                  type="button"
                  className="btn-link"
                  onClick={handleResendOTP}
                  disabled={loading}
                  style={{ color: portalDesign?.primary_color }}
                >
                  Resend OTP
                </button>
              )}
            </div>

            {/* Verify Button */}
            <button
              type="submit"
              className="btn btn-primary btn-block"
              disabled={loading || otp.join('').length !== 6}
              style={{ background: portalDesign?.primary_color }}
            >
              {loading ? (
                <span className="btn-loading">
                  <span className="spinner-small"></span>
                  Verifying...
                </span>
              ) : (
                <>
                  Verify & Connect
                  <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor" style={{ marginLeft: '8px' }}>
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                </>
              )}
            </button>

            {/* Back Button */}
            <button
              type="button"
              className="btn btn-secondary btn-block"
              onClick={() => {
                setStep('info');
                setOtp(['', '', '', '', '', '']);
                setTimer(0);
              }}
              disabled={loading}
            >
              <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor" style={{ marginRight: '8px' }}>
                <path fillRule="evenodd" d="M9.707 16.707a1 1 0 01-1.414 0l-6-6a1 1 0 010-1.414l6-6a1 1 0 011.414 1.414L5.414 9H17a1 1 0 110 2H5.414l4.293 4.293a1 1 0 010 1.414z" clipRule="evenodd" />
              </svg>
              Change Number
            </button>
          </form>
        )}
      </div>

      {showTerms && (
        <TermsModal
          portalDesign={portalDesign}
          onClose={() => setShowTerms(false)}
        />
      )}
    </>
  );
}

export default LoginForm;
