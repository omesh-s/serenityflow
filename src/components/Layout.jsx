import React, { useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { motion } from 'framer-motion';
import { IoHomeOutline, IoSettingsOutline, IoLogOutOutline } from 'react-icons/io5';
import { useAuth } from '../hooks/useAuth';
import { useTheme } from '../hooks/useTheme.jsx';
import { useSoundControl } from '../hooks/useSoundControl';
import { hexToRgba } from '../utils/hexToRgb';
import logo from '../assets/SerenityLogo.png';
import { IoVolumeHigh, IoVolumeMute } from 'react-icons/io5';

const Layout = ({ children }) => {
  const location = useLocation();
  const { user, logout, checkAuthStatus } = useAuth();
  const { themeColors } = useTheme();
  const { isMuted, toggleMute } = useSoundControl();
  
  // Note: User info will be fetched automatically by useAuth hook
  // If user name is "User", it means user info is not available yet
  // This can happen if:
  // 1. User authenticated before we added userinfo scopes (need to re-authenticate)
  // 2. User info is still being fetched from Google API
  // The backend will automatically fetch user info when /auth/status is called
  
  // Get theme-based background gradient
  const getBackgroundStyle = () => {
    if (!themeColors) {
      return 'bg-gradient-to-br from-ocean-50 via-calm-mist to-serenity-light';
    }
    return {
      background: `linear-gradient(135deg, ${themeColors.backgroundStart} 0%, #f5f9fa 50%, ${themeColors.backgroundEnd} 100%)`,
    };
  };

  return (
    <div 
      className="min-h-screen relative overflow-hidden transition-all duration-500 ease-in-out"
      style={getBackgroundStyle()}
    >
      {/* Animated background waves with theme colors */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <motion.div 
          className="absolute -top-1/2 -left-1/4 w-96 h-96 rounded-full blur-3xl animate-float"
          style={{ 
            backgroundColor: themeColors ? hexToRgba(themeColors.primaryLight, 0.2) : 'rgba(14, 165, 233, 0.2)',
            transition: 'background-color 0.5s ease-in-out'
          }}
        ></motion.div>
        <motion.div 
          className="absolute top-1/3 -right-1/4 w-[600px] h-[600px] rounded-full blur-3xl animate-wave"
          style={{ 
            backgroundColor: themeColors ? hexToRgba(themeColors.primary, 0.3) : 'rgba(184, 221, 230, 0.3)',
            transition: 'background-color 0.5s ease-in-out'
          }}
        ></motion.div>
        <motion.div 
          className="absolute bottom-0 left-1/3 w-96 h-96 rounded-full blur-3xl animate-float" 
          style={{ 
            animationDelay: '2s',
            backgroundColor: themeColors ? hexToRgba(themeColors.accent, 0.2) : 'rgba(14, 165, 233, 0.2)',
            transition: 'background-color 0.5s ease-in-out'
          }}
        ></motion.div>
      </div>

      {/* Navigation */}
      <nav className="relative z-10 glass-card mx-4 mt-4 px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <Link to="/" className="flex items-center space-x-3 group">
            <motion.div 
              className="w-10 h-10 flex items-center justify-center group-hover:scale-110 transition-transform"
              style={{
                transition: 'transform 0.3s ease-in-out'
              }}
            >
              <img 
                src={logo} 
                alt="Serenity Logo" 
                className="w-full h-full object-contain"
              />
            </motion.div>
            <h1 
              className="text-2xl font-bold bg-clip-text text-transparent"
              style={{
                backgroundImage: themeColors
                  ? `linear-gradient(to right, ${themeColors.primaryDark}, ${themeColors.primary})`
                  : 'linear-gradient(to right, #0369a1, #0ea5e9)',
                transition: 'background-image 0.5s ease-in-out'
              }}
            >
              Serenity
            </h1>
          </Link>

          <div className="flex items-center space-x-6">
            <NavLink to="/" icon={IoHomeOutline} active={location.pathname === '/'}>
              Dashboard
            </NavLink>
            <NavLink to="/settings" icon={IoSettingsOutline} active={location.pathname === '/settings'}>
              Settings
            </NavLink>
            
            {/* Mute/Unmute Button */}
            <button
              onClick={toggleMute}
              className="p-2 rounded-lg transition-colors"
              style={{
                color: themeColors ? themeColors.textLight : '#0284c7',
                transition: 'all 0.3s ease-in-out'
              }}
              onMouseEnter={(e) => {
                if (themeColors) {
                  e.currentTarget.style.backgroundColor = hexToRgba(themeColors.primaryLight, 0.1);
                }
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.backgroundColor = 'transparent';
              }}
              title={isMuted ? 'Unmute sounds' : 'Mute sounds'}
            >
              {isMuted ? <IoVolumeMute size={20} /> : <IoVolumeHigh size={20} />}
            </button>
            
            {user && (
              <div 
                className="flex items-center space-x-4 ml-4 pl-4 border-l"
                style={{
                  borderColor: themeColors ? hexToRgba(themeColors.primary, 0.25) : 'rgba(14, 165, 233, 0.2)',
                  transition: 'border-color 0.5s ease-in-out'
                }}
              >
                <span 
                  className="text-sm font-medium"
                  style={{
                    color: themeColors ? themeColors.textLight : '#0284c7',
                    transition: 'color 0.5s ease-in-out'
                  }}
                  title={user.email || 'User'}
                >
                  {user.name || 'User'}
                </span>
                <button
                  onClick={logout}
                  className="p-2 rounded-lg transition-colors"
                  style={{
                    color: themeColors ? themeColors.textLight : '#0284c7',
                    transition: 'all 0.3s ease-in-out'
                  }}
                  onMouseEnter={(e) => {
                    if (themeColors) {
                      e.currentTarget.style.backgroundColor = hexToRgba(themeColors.primaryLight, 0.1);
                    }
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.backgroundColor = 'transparent';
                  }}
                  title="Logout"
                >
                  <IoLogOutOutline size={20} />
                </button>
              </div>
            )}
          </div>
        </div>
      </nav>

      {/* Main content */}
      <main className="relative z-10 max-w-7xl mx-auto px-4 py-8">
        {children}
      </main>
    </div>
  );
};

const NavLink = ({ to, icon: Icon, active, children }) => {
  const { themeColors } = useTheme();
  
  // Get hover color with opacity
  const getHoverColor = () => {
    if (!themeColors) return 'rgba(14, 165, 233, 0.1)';
    try {
      return hexToRgba(themeColors.primary, 0.1);
    } catch (e) {
      return 'rgba(14, 165, 233, 0.1)';
    }
  };
  
  return (
    <Link
      to={to}
      className="flex items-center space-x-2 px-4 py-2 rounded-lg transition-all duration-300"
      style={{
        backgroundColor: active && themeColors ? themeColors.primary : 'transparent',
        color: active ? 'white' : (themeColors ? themeColors.text : '#0284c7'),
        transition: 'all 0.3s ease-in-out'
      }}
      onMouseEnter={(e) => {
        if (!active && themeColors) {
          try {
            e.currentTarget.style.backgroundColor = getHoverColor();
          } catch (err) {
            // Ignore hover errors
          }
        }
      }}
      onMouseLeave={(e) => {
        if (!active) {
          e.currentTarget.style.backgroundColor = 'transparent';
        }
      }}
    >
      <Icon size={20} />
      <span className="font-medium">{children}</span>
    </Link>
  );
};

export default Layout;
