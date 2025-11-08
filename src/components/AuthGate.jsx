import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { useAuth } from '../hooks/useAuth';
import { GOOGLE_CLIENT_ID } from '../utils/constants';

/**
 * Authentication page with Google OAuth
 * TODO: Implement Google Identity Services (GIS) integration
 * See: https://developers.google.com/identity/gsi/web/guides/overview
 */
const AuthGate = () => {
  const navigate = useNavigate();
  const { login, isAuthenticated } = useAuth();

  useEffect(() => {
    if (isAuthenticated) {
      navigate('/', { replace: true });
    }
  }, [isAuthenticated, navigate]);

  useEffect(() => {
    // TODO: Load Google Identity Services script
    // const script = document.createElement('script');
    // script.src = 'https://accounts.google.com/gsi/client';
    // script.async = true;
    // script.defer = true;
    // document.body.appendChild(script);

    // script.onload = () => {
    //   window.google.accounts.id.initialize({
    //     client_id: GOOGLE_CLIENT_ID,
    //     callback: handleGoogleResponse,
    //   });
    //   
    //   window.google.accounts.id.renderButton(
    //     document.getElementById('google-signin-button'),
    //     { theme: 'outline', size: 'large', width: 250 }
    //   );
    // };
  }, []);

  const handleGoogleResponse = async (response) => {
    try {
      // TODO: Send credential to backend for verification
      const success = await login(response.credential);
      if (success) {
        navigate('/', { replace: true });
      }
    } catch (error) {
      console.error('Google login failed:', error);
    }
  };

  const mockLogin = async () => {
    // Mock login for development
    await login('mock_google_token');
    navigate('/', { replace: true });
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
          <div className="w-20 h-20 mx-auto rounded-full ocean-gradient flex items-center justify-center mb-4 animate-breath">
            <span className="text-4xl">🌊</span>
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
          {/* TODO: Replace with actual Google Sign-In button */}
          <div id="google-signin-button" className="flex justify-center"></div>
          
          {/* Mock login for development */}
          <button
            onClick={mockLogin}
            className="w-full btn-primary"
          >
            Continue with Google (Dev Mode)
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
