import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { motion } from 'framer-motion';
import { IoHomeOutline, IoSettingsOutline, IoLogOutOutline } from 'react-icons/io5';
import { useAuth } from '../hooks/useAuth';

const Layout = ({ children }) => {
  const location = useLocation();
  const { user, logout } = useAuth();

  return (
    <div className="min-h-screen bg-gradient-to-br from-ocean-50 via-calm-mist to-serenity-light relative overflow-hidden">
      {/* Animated background waves */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-1/2 -left-1/4 w-96 h-96 bg-ocean-200/20 rounded-full blur-3xl animate-float"></div>
        <div className="absolute top-1/3 -right-1/4 w-[600px] h-[600px] bg-serenity/30 rounded-full blur-3xl animate-wave"></div>
        <div className="absolute bottom-0 left-1/3 w-96 h-96 bg-ocean-300/20 rounded-full blur-3xl animate-float" style={{ animationDelay: '2s' }}></div>
      </div>

      {/* Navigation */}
      <nav className="relative z-10 glass-card mx-4 mt-4 px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <Link to="/" className="flex items-center space-x-3 group">
            <div className="w-10 h-10 rounded-full ocean-gradient flex items-center justify-center group-hover:scale-110 transition-transform">
              <span className="text-white text-xl">🌊</span>
            </div>
            <h1 className="text-2xl font-bold bg-gradient-to-r from-ocean-600 to-ocean-400 bg-clip-text text-transparent">
              SerenityFlow
            </h1>
          </Link>

          <div className="flex items-center space-x-6">
            <NavLink to="/" icon={IoHomeOutline} active={location.pathname === '/'}>
              Dashboard
            </NavLink>
            <NavLink to="/settings" icon={IoSettingsOutline} active={location.pathname === '/settings'}>
              Settings
            </NavLink>
            
            {user && (
              <div className="flex items-center space-x-4 ml-4 pl-4 border-l border-ocean-200">
                <span className="text-sm text-ocean-600">{user.name}</span>
                <button
                  onClick={logout}
                  className="p-2 text-ocean-600 hover:text-ocean-800 hover:bg-ocean-50 rounded-lg transition-colors"
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

const NavLink = ({ to, icon: Icon, active, children }) => (
  <Link
    to={to}
    className={`flex items-center space-x-2 px-4 py-2 rounded-lg transition-all ${
      active
        ? 'bg-ocean-500 text-white shadow-lg'
        : 'text-ocean-600 hover:bg-ocean-50'
    }`}
  >
    <Icon size={20} />
    <span className="font-medium">{children}</span>
  </Link>
);

export default Layout;
