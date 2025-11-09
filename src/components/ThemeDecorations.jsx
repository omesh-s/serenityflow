import React from 'react';
import { motion } from 'framer-motion';
import { useTheme } from '../hooks/useTheme';
import { hexToRgba } from '../utils/hexToRgb';

/**
 * Theme-based decorative elements for the dashboard
 * Displays calm, animated stickers/pictures in bottom corners based on theme
 */
const ThemeDecorations = () => {
  const { currentTheme, themeColors } = useTheme();

  // Theme-specific decorations with positioning and animation data
  // Only 2 elements per corner for a cleaner look
  const decorations = {
    ocean: {
      bottomLeft: {
        elements: [
          { emoji: '🌊', delay: 0, duration: 5, offset: 0 },
          { emoji: '🐚', delay: 0.5, duration: 4.5, offset: -10 }
        ],
        description: 'Ocean waves and sea creatures'
      },
      bottomRight: {
        elements: [
          { emoji: '🐟', delay: 0.3, duration: 4.8, offset: 5 },
          { emoji: '🌊', delay: 0.8, duration: 5.2, offset: -8 }
        ],
        description: 'Ocean waves and fish'
      }
    },
    forest: {
      bottomLeft: {
        elements: [
          { emoji: '🌲', delay: 0, duration: 6, offset: 0 },
          { emoji: '🍃', delay: 0.6, duration: 4, offset: -12 }
        ],
        description: 'Trees and forest life'
      },
      bottomRight: {
        elements: [
          { emoji: '🦋', delay: 0.2, duration: 4.2, offset: 6 },
          { emoji: '🌿', delay: 0.7, duration: 4.5, offset: -10 }
        ],
        description: 'Forest plants and wildlife'
      }
    },
    rain: {
      bottomLeft: {
        elements: [
          { emoji: '☁️', delay: 0, duration: 5.5, offset: 0 },
          { emoji: '🌧️', delay: 0.5, duration: 4, offset: -10 }
        ],
        description: 'Rain and clouds'
      },
      bottomRight: {
        elements: [
          { emoji: '☔', delay: 0.3, duration: 4.5, offset: 5 },
          { emoji: '💧', delay: 0.8, duration: 3.8, offset: -8 }
        ],
        description: 'Raindrops and umbrellas'
      }
    },
    wind: {
      bottomLeft: {
        elements: [
          { emoji: '🍃', delay: 0, duration: 3.5, offset: 0 },
          { emoji: '🎐', delay: 0.5, duration: 5, offset: -12 }
        ],
        description: 'Wind and leaves'
      },
      bottomRight: {
        elements: [
          { emoji: '🌸', delay: 0.2, duration: 4.8, offset: 6 },
          { emoji: '🍂', delay: 0.7, duration: 3.8, offset: -10 }
        ],
        description: 'Wind chimes and flowers'
      }
    }
  };

  const themeDecorations = decorations[currentTheme] || decorations.ocean;

  // Create floating animation for each element
  const createFloatingAnimation = (delay, duration, offset) => {
    return {
      y: [0, -20 + offset, 0],
      x: [0, 8 + offset * 0.5, 0],
      rotate: [0, 8, -8, 0],
      scale: [1, 1.1, 1],
      transition: {
        duration: duration,
        delay: delay,
        repeat: Infinity,
        ease: "easeInOut",
        times: [0, 0.5, 1]
      }
    };
  };

  // Stagger animation for container
  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.2,
        delayChildren: 0.5
      }
    }
  };

  const itemVariants = {
    hidden: { 
      opacity: 0, 
      scale: 0.5, 
      y: 30,
      rotate: -10
    },
    visible: {
      opacity: 0.7,
      scale: 1,
      y: 0,
      rotate: 0,
      transition: {
        duration: 0.8,
        ease: "easeOut",
        type: "spring",
        stiffness: 100
      }
    }
  };

  // Render decoration elements
  const renderDecorations = (elements, position) => {
    const isLeft = position === 'bottomLeft';
    
    // Adjust positioning to avoid overlapping with widgets
    // Bottom right needs more space for ConvaiWidget (approximately 80px height)
    const bottomClass = isLeft ? 'bottom-4 md:bottom-6' : 'bottom-20 md:bottom-24';
    const horizontalClass = isLeft ? 'left-4 md:left-6' : 'right-4 md:right-6';
    
    return (
      <motion.div
        variants={containerVariants}
        initial="hidden"
        animate="visible"
        className={`fixed ${bottomClass} ${horizontalClass} z-0 pointer-events-none hidden md:block`}
        style={{
          maxWidth: '140px',
          opacity: 0.7
        }}
      >
        <div className={`relative flex flex-col ${isLeft ? 'items-start' : 'items-end'} space-y-4 md:space-y-5 lg:space-y-6`}>
          {elements.map((item, index) => {
            const floatingAnim = createFloatingAnimation(
              item.delay, 
              item.duration, 
              item.offset
            );
            
            return (
              <motion.div
                key={index}
                variants={itemVariants}
                animate={floatingAnim}
                style={{
                  filter: `drop-shadow(0 4px 8px ${hexToRgba(themeColors?.primaryLight || '#38bdf8', 0.3)})`,
                  transformOrigin: 'center',
                }}
                className="text-3xl md:text-4xl lg:text-5xl xl:text-6xl select-none"
                whileHover={{
                  scale: 1.15,
                  rotate: 8,
                  transition: { duration: 0.3 }
                }}
              >
                {item.emoji}
              </motion.div>
            );
          })}
        </div>
      </motion.div>
    );
  };

  return (
    <>
      {/* Bottom Left Decorations */}
      {renderDecorations(themeDecorations.bottomLeft.elements, 'bottomLeft')}
      
      {/* Bottom Right Decorations */}
      {renderDecorations(themeDecorations.bottomRight.elements, 'bottomRight')}
    </>
  );
};

export default ThemeDecorations;

