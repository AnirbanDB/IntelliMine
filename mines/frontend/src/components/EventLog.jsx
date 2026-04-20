import { useRef, useEffect } from 'react';

const CAT_STYLE = {
  CRITICAL:     { color: '#ff2200', emoji: '🔴', glow: true },
  HAZARD:       { color: '#ff8800', emoji: '⚠', glow: false },
  HAZARD_CLEAR: { color: '#22dd55', emoji: '✓', glow: false },
  SYSTEM:       { color: '#8a7860', emoji: '⚙', glow: false },
  WARNING:      { color: '#ffcc44', emoji: '!', glow: false },
  INFO:         { color: '#5e8aaa', emoji: 'i', glow: false },
};

export default function EventFeed({ events = [] }) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [events.length]);

  return (
    <div className="font-data flex flex-col" style={{ height: '220px', borderTop: '1px solid #3d3020' }}>
      <div className="game-header shrink-0">📡 EVENT FEED</div>

      <div className="flex-1 overflow-y-auto px-2 py-1 space-y-1">
        {events.length === 0 && (
          <div className="font-pixel text-[6px] text-g-dim text-center pt-4">
            AWAITING SIGNALS...
          </div>
        )}
        {[...events].reverse().slice(0, 40).map((ev, i) => {
          const s = CAT_STYLE[ev.category] || CAT_STYLE.INFO;
          return (
            <div key={i} className="flex gap-1.5 items-start animate-rise py-0.5"
                 style={{ borderBottom: '1px solid #1a1612' }}>
              <span className="text-[9px] shrink-0 mt-0.5">{s.emoji}</span>
              <div className="flex-1 min-w-0">
                <span className="font-pixel text-[5px] mr-1"
                      style={{ color: s.color, textShadow: s.glow ? `0 0 6px ${s.color}` : 'none' }}>
                  {ev.category}
                </span>
                <span className="font-data text-[9px] text-g-muted break-words">
                  {ev.message}
                </span>
              </div>
              <span className="font-pixel text-[5px] text-g-dim shrink-0">T{ev.tick}</span>
            </div>
          );
        })}
        <div ref={bottomRef}/>
      </div>
    </div>
  );
}
