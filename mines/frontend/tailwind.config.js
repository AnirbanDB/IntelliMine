/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        g: {
          bg:      '#070503',
          stone:   '#1e1a14',
          stone2:  '#2a2218',
          panel:   '#0f0c07',
          border:  '#6b4c1e',
          border2: '#9a6e2e',
          ore:     '#ffaa22',
          ore2:    '#ff8800',
          exit:    '#22dd55',
          exit2:   '#15a33a',
          danger:  '#ff2200',
          danger2: '#cc1500',
          warn:    '#ffaa00',
          safe:    '#22dd55',
          torch:   '#ffbb44',
          truck:   '#00ddff',
          worker:  '#f0e6cc',
          text:    '#f0e6cc',
          muted:   '#8a7860',
          dim:     '#3d3020',
          lava:    '#ff5500',
          diamond: '#88eeff',
        },
        // keep old mine prefix so existing refs don't explode
        mine: {
          dark:    '#0a0a0c',
          darker:  '#050506',
          accent:  '#00f2ff',
          hazard:  '#ff2d55',
          safe:    '#00ff9d',
          warning: '#ffcc00',
        },
      },
      fontFamily: {
        pixel: ['"Press Start 2P"', 'monospace'],
        data:  ['"Share Tech Mono"', '"Courier New"', 'monospace'],
      },
      animation: {
        'ore-pulse':    'orePulse 2.5s ease-in-out infinite',
        'danger-flash': 'dangerFlash 0.7s ease-in-out infinite alternate',
        'torch':        'torchFlicker 0.12s ease-in-out infinite alternate',
        'march':        'march 0.5s linear infinite',
        'rise':         'rise 0.25s ease-out',
        'pulse-slow':   'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
      keyframes: {
        orePulse: {
          '0%,100%': { filter: 'drop-shadow(0 0 4px #ffaa22) brightness(1)' },
          '50%':     { filter: 'drop-shadow(0 0 14px #ffaa22) brightness(1.3)' },
        },
        dangerFlash: {
          '0%':   { filter: 'drop-shadow(0 0 5px #ff2200)', opacity: '0.8' },
          '100%': { filter: 'drop-shadow(0 0 18px #ff2200)', opacity: '1' },
        },
        torchFlicker: {
          '0%':   { opacity: '0.85', transform: 'scale(0.98)' },
          '100%': { opacity: '1',    transform: 'scale(1.02)' },
        },
        march: { to: { strokeDashoffset: '-12' } },
        rise: {
          from: { opacity: '0', transform: 'translateY(6px)' },
          to:   { opacity: '1', transform: 'translateY(0)' },
        },
      },
    },
  },
  plugins: [],
}
