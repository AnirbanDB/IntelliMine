import { useMemo } from 'react';

const ACT_COLOR = {
  blast:  { bg: 'rgba(200,80,0,0.85)',  border: '#ff5500', text: '#ffcc88', emoji: '💥' },
  drill:  { bg: 'rgba(0,80,160,0.85)',  border: '#0088ff', text: '#88ccff', emoji: '⛏' },
  load:   { bg: 'rgba(0,130,50,0.85)',  border: '#00cc44', text: '#88ffaa', emoji: '📦' },
  idle:   { bg: 'rgba(30,25,15,0.5)',   border: '#3d3020', text: '#5a4830', emoji: '·' },
  halted: { bg: 'rgba(180,0,0,0.7)',    border: '#ff2200', text: '#ffaaaa', emoji: '⛔' },
};

const fallback = { bg: 'transparent', border: '#3d3020', text: '#5a4830', emoji: '?' };

export default function ScheduleStrip({ schedule = [], parameters = {} }) {
  const numSlots = parameters?.schedule?.num_time_slots ?? 12;

  const { zones, map: schedMap } = useMemo(() => {
    const map = {};
    schedule.forEach(s => {
      if (!map[s.zone_id]) map[s.zone_id] = {};
      map[s.zone_id][s.time_slot] = s.activity;
    });
    return { zones: Object.keys(map).sort(), map };
  }, [schedule]);

  if (!zones.length) return null;

  return (
    <div className="font-data" style={{ borderTop: '2px solid #6b4c1e' }}>
      {/* Header */}
      <div className="game-header flex items-center justify-between">
        <span>📋 CSP SCHEDULE — GANTT</span>
        <div className="flex gap-3 text-[6px]">
          {Object.entries(ACT_COLOR).map(([act, s]) => (
            <span key={act} style={{ color: s.text }}>
              {s.emoji} {act.toUpperCase()}
            </span>
          ))}
        </div>
      </div>

      {/* Grid */}
      <div className="overflow-x-auto" style={{ maxHeight: '120px' }}>
        <table style={{ borderCollapse: 'collapse', width: '100%', tableLayout: 'fixed' }}>
          <colgroup>
            <col style={{ width: '72px' }}/>
            {Array.from({ length: numSlots }, (_, i) => (
              <col key={i} style={{ width: '32px' }}/>
            ))}
          </colgroup>
          <thead>
            <tr style={{ borderBottom: '1px solid #3d3020' }}>
              <th className="px-2 py-1 text-left font-pixel text-[6px] text-g-muted">ZONE</th>
              {Array.from({ length: numSlots }, (_, i) => (
                <th key={i} className="text-center font-pixel text-[5px] text-g-dim py-1">
                  T{i+1}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {zones.map(zoneId => (
              <tr key={zoneId} style={{ borderBottom: '1px solid #1a1612' }}>
                <td className="px-2 py-0.5 font-data text-[9px] text-g-muted truncate"
                    style={{ borderRight: '1px solid #3d3020' }}>
                  {zoneId}
                </td>
                {Array.from({ length: numSlots }, (_, t) => {
                  const act = schedMap[zoneId]?.[t] || 'idle';
                  const style = ACT_COLOR[act] || fallback;
                  return (
                    <td key={t} title={act}
                        className="text-center py-0.5"
                        style={{
                          background: style.bg,
                          borderRight: `1px solid ${style.border}22`,
                          fontSize: '10px',
                          lineHeight: '1',
                        }}>
                      {style.emoji}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
