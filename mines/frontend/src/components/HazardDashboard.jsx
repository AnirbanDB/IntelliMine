import { useMemo } from 'react';

// ── Pixel-style bar ───────────────────────────────────────────────────
function PxBar({ value, color = '#ff2200' }) {
  const pct = Math.min(100, Math.max(0, value * 100));
  return (
    <div className="px-bar-track">
      <div className="px-bar-fill" style={{ width: `${pct.toFixed(1)}%`, background: color }}/>
    </div>
  );
}

// ── Sensor row ────────────────────────────────────────────────────────
function SensorRow({ emoji, label, value }) {
  const pct = Math.min(1, value);
  const color =
    pct > 0.75 ? '#ff2200' :
    pct > 0.5  ? '#ffaa00' :
    pct > 0.25 ? '#ffcc44' : '#22dd55';
  return (
    <div className="mb-2">
      <div className="flex items-center justify-between mb-1">
        <span className="font-data text-[9px] text-g-muted flex items-center gap-1">
          <span>{emoji}</span>{label}
        </span>
        <span className="font-pixel text-[7px]" style={{ color }}>{pct.toFixed(2)}</span>
      </div>
      <PxBar value={pct} color={color}/>
    </div>
  );
}

export default function HazardDashboard({ hazard_probabilities = {}, sensor_readings = {}, active_hazards = [] }) {
  const probs = Object.values(hazard_probabilities);
  const peak  = probs.length ? Math.max(...probs) : 0;

  const sensors = useMemo(() => {
    const readings = Object.values(sensor_readings);
    if (!readings.length) return { gas: 0, vib: 0, blast: 0, moist: 0 };
    const n = readings.length;
    return {
      gas:   readings.reduce((s,r)=>s+(r.gas_level||0),   0)/n,
      vib:   readings.reduce((s,r)=>s+(r.vibration||0),   0)/n,
      blast: readings.reduce((s,r)=>s+(r.blast_activity||0),0)/n,
      moist: readings.reduce((s,r)=>s+(r.moisture||0),    0)/n,
    };
  }, [sensor_readings]);

  const hotNodes = useMemo(() =>
    Object.entries(hazard_probabilities).sort(([,a],[,b])=>b-a).slice(0,4),
  [hazard_probabilities]);

  const bayesToxic    = Math.min(1, sensors.gas*0.7 + sensors.blast*0.3 + sensors.gas*sensors.blast*0.5);
  const bayesCollapse = Math.min(1, sensors.vib*0.6 + sensors.moist*0.2 + sensors.vib*sensors.moist*0.8);
  const bayesOverall  = bayesToxic + bayesCollapse - bayesToxic*bayesCollapse;

  const alertLabel =
    peak > 0.85 ? { txt: '☣ CRITICAL', color: '#ff2200' } :
    peak > 0.6  ? { txt: '⚠ ELEVATED', color: '#ffaa00' } :
    peak > 0.3  ? { txt: '! CAUTION',  color: '#ffcc44' } :
                  { txt: '✓ STABLE',   color: '#22dd55' };

  return (
    <div className="font-data">
      {/* Header */}
      <div className="game-header">☣ HAZARD MONITOR</div>

      <div className="px-3 pt-2 pb-1">
        {/* Alert level */}
        <div className="flex items-center justify-between mb-2 p-2"
             style={{ background: 'rgba(0,0,0,0.4)', border: '1px solid #3d3020' }}>
          <span className="font-pixel text-[8px]" style={{ color: alertLabel.color,
            textShadow: `0 0 8px ${alertLabel.color}` }}>
            {alertLabel.txt}
          </span>
          <div className="text-right">
            <div className="font-pixel text-[6px] text-g-muted">PEAK</div>
            <div className="font-pixel text-[8px] text-g-ore">{(peak*100).toFixed(0)}%</div>
          </div>
        </div>

        {/* Sensors */}
        <div className="text-[7px] font-pixel text-g-muted mb-2 mt-1">SENSORS</div>
        <SensorRow emoji="💨" label="Gas"       value={sensors.gas}/>
        <SensorRow emoji="📳" label="Vibration" value={sensors.vib}/>
        <SensorRow emoji="💥" label="Blast"     value={sensors.blast}/>
        <SensorRow emoji="💧" label="Moisture"  value={sensors.moist}/>

        {/* Bayesian */}
        <div className="text-[7px] font-pixel text-g-muted mb-2 mt-3">BAYES NET</div>
        <SensorRow emoji="☠" label="Toxic Risk"    value={bayesToxic}/>
        <SensorRow emoji="🪨" label="Collapse Risk" value={bayesCollapse}/>
        <SensorRow emoji="☣" label="Overall P(H)"  value={bayesOverall}/>

        {/* Hot zones */}
        {hotNodes.length > 0 && (
          <>
            <div className="text-[7px] font-pixel text-g-muted mb-2 mt-3">HOT ZONES</div>
            {hotNodes.map(([id, p]) => (
              <div key={id} className="flex items-center gap-2 mb-1.5">
                <span className={`text-[8px] ${p > 0.6 ? 'text-g-danger animate-pulse' : 'text-g-warn'}`}>
                  {p > 0.6 ? '🔥' : '⚠'}
                </span>
                <span className="font-data text-[9px] text-g-muted flex-1 truncate">{id}</span>
                <span className="font-pixel text-[7px]"
                      style={{ color: p > 0.6 ? '#ff2200' : '#ffaa00' }}>
                  {(p*100).toFixed(0)}%
                </span>
              </div>
            ))}
          </>
        )}

        {/* Active hazard events */}
        {active_hazards.length > 0 && (
          <>
            <div className="text-[7px] font-pixel text-g-danger mb-1 mt-3 animate-pulse">
              ⚠ ACTIVE EVENTS ({active_hazards.length})
            </div>
            {active_hazards.slice(0,3).map(h => (
              <div key={h.id} className="mb-1 px-2 py-1 text-[9px] font-data"
                   style={{ background:'rgba(255,34,0,0.1)', border:'1px solid rgba(255,34,0,0.3)' }}>
                <span className="text-g-danger font-pixel text-[6px]">
                  {(h.type||h.hazard_type||'').replace('_',' ').toUpperCase()}
                </span>
                <span className="text-g-muted ml-1 text-[8px]">{h.node_id}</span>
                <span className="text-g-danger float-right font-pixel text-[7px]">
                  {(h.severity*100).toFixed(0)}%
                </span>
              </div>
            ))}
          </>
        )}
      </div>
    </div>
  );
}
