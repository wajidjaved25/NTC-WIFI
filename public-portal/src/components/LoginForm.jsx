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
      setError('');
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to resend OTP');
    } finally {
      setLoading(false);
    }
  };

  const formatMobile = (mobile) => {
    // Format: 03XX-XXXXXXX
    mobile = mobile.replace(/\D/g, '');
    if (mobile.startsWith('+92')) {
      mobile = '0' + mobile.slice(3);
    }
    return mobile;
  };

  const formatCNIC = (cnic) => {
    // Format: XXXXX-XXXXXXX-X
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
      <div className="portal-header">
        {portalDesign?.show_logo && portalDesign?.logo_path && (
          <img
            src={portalDesign.logo_path}
            alt="Logo"
            className="portal-logo"
          />
        )}
        <h1 className="portal-title" style={{ color: portalDesign?.primary_color }}>
          {portalDesign?.welcome_title}
        </h1>
        <div 
          className="portal-subtitle"
          dangerouslySetInnerHTML={{ __html: portalDesign?.welcome_text || '' }}
        />
      </div>

      <div className="portal-body">
        {error && <div className="message message-error">{error}</div>}

        {step === 'info' && (
          <form onSubmit={handleSendOTP}>
            <div className="form-group">
              <label className="form-label">Full Name *</label>
              <input
                type="text"
                name="name"
                className="form-input"
                value={formData.name}
                onChange={handleInputChange}
                placeholder="Enter your full name"
                required
              />
            </div>

            <div className="form-group">
              <label className="form-label">Mobile Number *</label>
              <input
                type="tel"
                name="mobile"
                className="form-input"
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

            <div className="form-group">
              <label className="form-label">ID Type *</label>
              <select
                name="id_type"
                className="form-select"
                value={formData.id_type}
                onChange={handleInputChange}
              >
                <option value="cnic">CNIC</option>
                <option value="passport">Passport</option>
              </select>
            </div>

            {formData.id_type === 'cnic' ? (
              <div className="form-group">
                <label className="form-label">CNIC Number *</label>
                <input
                  type="text"
                  name="cnic"
                  className="form-input"
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
            ) : (
              <div className="form-group">
                <label className="form-label">Passport Number *</label>
                <input
                  type="text"
                  name="passport"
                  className="form-input"
                  value={formData.passport}
                  onChange={handleInputChange}
                  placeholder="Enter passport number"
                  required
                />
              </div>
            )}

            <div className="form-group">
              <div className="form-checkbox">
                <input
                  type="checkbox"
                  name="terms_accepted"
                  id="terms"
                  checked={formData.terms_accepted}
                  onChange={handleInputChange}
                  required
                />
                <label htmlFor="terms">
                  I accept the{' '}
                  <a
                    href="#"
                    onClick={(e) => {
                      e.preventDefault();
                      setShowTerms(true);
                    }}
                  >
                    Terms and Conditions
                  </a>
                </label>
              </div>
            </div>

            <button
              type="submit"
              className="btn btn-primary"
              disabled={loading}
              style={{ background: portalDesign?.primary_color }}
            >
              {loading ? 'Sending OTP...' : 'Send OTP'}
            </button>
          </form>
        )}

        {step === 'otp' && (
          <form onSubmit={handleVerifyOTP}>
            <div className="message message-info">
              OTP sent to {formData.mobile}
            </div>

            <div className="form-group">
              <label className="form-label" style={{ textAlign: 'center' }}>
                Enter 6-Digit OTP
              </label>
              <div className="otp-container">
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
                    style={{ borderColor: portalDesign?.primary_color }}
                  />
                ))}
              </div>
            </div>

            {timer > 0 && (
              <div className="timer">
                Resend OTP in {Math.floor(timer / 60)}:{(timer % 60).toString().padStart(2, '0')}
              </div>
            )}

            {timer === 0 && (
              <div style={{ textAlign: 'center', marginBottom: '15px' }}>
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={handleResendOTP}
                  disabled={loading}
                  style={{
                    background: 'transparent',
                    color: portalDesign?.primary_color,
                    border: 'none',
                    cursor: 'pointer',
                    textDecoration: 'underline',
                  }}
                >
                  Resend OTP
                </button>
              </div>
            )}

            <button
              type="submit"
              className="btn btn-primary"
              disabled={loading}
              style={{ background: portalDesign?.primary_color }}
            >
              {loading ? 'Verifying...' : 'Verify & Continue'}
            </button>

            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => {
                setStep('info');
                setOtp(['', '', '', '', '', '']);
                setTimer(0);
              }}
              disabled={loading}
              style={{ marginTop: '10px' }}
            >
              Change Mobile Number
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
