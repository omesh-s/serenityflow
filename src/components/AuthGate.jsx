import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { motion } from 'framer-motion';
import { useAuth } from '../hooks/useAuth';
import logo from '../assets/SerenityLogo.png';

/**
 * Authentication page with Google OAuth
 * Connects to backend OAuth flow
 */
const AuthGate = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { isAuthenticated, initiateGoogleLogin, checkAuthStatus } = useAuth();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Handle OAuth callback
  useEffect(() => {
    const service = searchParams.get('service');
    const success = searchParams.get('success');
    
    if (service && success === 'true') {
      // OAuth callback successful, check auth status
      setTimeout(() => {
        checkAuthStatus();
        navigate('/', { replace: true });
      }, 1000);
    } else if (service && success === 'false') {
      setError('Authentication failed. Please try again.');
    }
  }, [searchParams, navigate, checkAuthStatus]);

  useEffect(() => {
    if (isAuthenticated) {
      navigate('/', { replace: true });
    }
  }, [isAuthenticated, navigate]);

  const handleGoogleLogin = async () => {
    try {
      setLoading(true);
      setError(null);
      await initiateGoogleLogin();
      // User will be redirected to Google, then back to /auth/callback
    } catch (err) {
      console.error('Google login failed:', err);
      setError('Failed to initiate Google login. Please try again.');
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-ocean-50 via-calm-mist to-serenity-light flex items-center justify-center relative overflow-hidden">
      {/* Animated background */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-ocean-200/30 rounded-full blur-3xl animate-float"></div>
        <div className="absolute bottom-1/4 right-1/4 w-[500px] h-[500px] bg-serenity/40 rounded-full blur-3xl animate-wave"></div>
      </div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
        className="relative z-10 glass-card p-12 max-w-md w-full text-center"
      >
        {/* Logo */}
        <div className="mb-8">
          <div className="w-24 h-24 mx-auto mb-4 flex items-center justify-center">
            <img 
              src={logo} 
              alt="SerenityFlow Logo" 
              className="w-full h-full object-contain"
              style={{ maxWidth: '96px', maxHeight: '96px' }}
            />
          </div>
          <h1 className="text-4xl font-bold bg-gradient-to-r from-ocean-600 to-ocean-400 bg-clip-text text-transparent mb-2">
            SerenityFlow
          </h1>
          <p className="text-ocean-600">Your automated productivity & stress companion</p>
        </div>

        {/* Benefits */}
        <div className="mb-8 text-left space-y-3">
          <BenefitItem icon="📅" text="Auto-sync with Google Calendar" />
          <BenefitItem icon="🧘" text="AI-powered break recommendations" />
          <BenefitItem icon="🎵" text="Guided meditation audio" />
          <BenefitItem icon="📊" text="Sentiment & mood analytics" />
        </div>

        {/* Google Sign In Button */}
        <div className="space-y-4">
          {error && (
            <div className="p-3 bg-red-100 border border-red-400 text-red-700 rounded-lg text-sm">
              {error}
            </div>
          )}
          
          <button
            onClick={handleGoogleLogin}
            disabled={loading}
            className="w-full btn-primary disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center space-x-2"
          >
            {loading ? (
              <>
                <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                <span>Connecting...</span>
              </>
            ) : (
              <>
                <svg className="w-5 h-5" viewBox="0 0 24 24">
                  <path fill="currentColor" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                  <path fill="currentColor" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                  <path fill="currentColor" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                  <path fill="currentColor" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                </svg>
                <span>Continue with Google</span>
              </>
            )}
          </button>
        </div>

        <p className="mt-6 text-xs text-ocean-500">
          By signing in, you agree to share your calendar data to provide personalized break recommendations.
        </p>
      </motion.div>
    </div>
  );
};

const BenefitItem = ({ icon, text }) => (
  <div className="flex items-center space-x-3">
    <span className="text-2xl">{icon}</span>
    <span className="text-ocean-700">{text}</span>
  </div>
);

export default AuthGate;
