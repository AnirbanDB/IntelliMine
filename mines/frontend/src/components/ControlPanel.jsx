import { useState } from 'react';

// ── Pixel-art section divider ─────────────────────────────────────────
function Section({ icon, title, children, defaultOpen = true }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="mb-1">
      <button
        className="w-full flex items-center gap-2 px-3 py-2 text-left hover:bg-white/5 transition-colors"
        style={{ borderBottom: '1px solid #3d3020' }}
        onClick={() => setOpen(v => !v)}
      >
        <span className="text-[10px]">{icon}</span>
        <span className="font-pixel text-[7px] text-g-torch tracking-widest flex-1">{title}</span>
        <span className="font-pixel text-[8px] text-g-muted">{open ? '▾' : '▸'}</span>
      </button>
      {open && <div className="px-3 pt-2 pb-1">{children}</div>}
    </div>
  );
}

// ── Single slider row ─────────────────────────────────────────────────
function Slider({ emoji, label, section, keyName, min, max, step, parameters, updateParam }) {
  const raw = parameters?.[section]?.[keyName];
  const val = raw !== undefined ? raw : min;
  const display = step < 1 ? Number(val).toFixed(2) : Number(val).toFixed(0);
  const pct = ((val - min) / (max - min)) * 100;

  return (
    <div className="mb-3">
      <div className="flex items-center justify-between mb-1">
        <span className="font-data text-[10px] text-g-muted flex items-center gap-1">
          <span>{emoji}</span> {label}
        </span>
        <span className="font-pixel text-[8px] text-g-ore">{display}</span>
      </div>
      <div className="relative">
        {/* Track */}
        <div className="px-bar-track">
          <div className="px-bar-fill bg-g-ore/70" style={{ width: `${pct}%` }}/>
        </div>
        <input
          type="range" min={min} max={max} step={step} value={val}
          onChange={e => updateParam(section, keyName, parseFloat(e.target.value))}
          className="game-slider absolute inset-0 opacity-0 cursor-pointer w-full"
          style={{ height: '8px' }}
        />
      </div>
    </div>
  );
}

export default function ControlPanel({ state, controls }) {
  const { status, parameters = {} } = state;
  const isRunning = status === 'running';
  const isPaused  = status === 'paused';

  const updateParam = (section, key, value) =>
    controls.updateParams({ [section]: { [key]: value } });

  const sp = { parameters, updateParam };

  return (
    <div className="h-full flex flex-col font-data">
      {/* ── Header ── */}
      <div className="game-header flex items-center justify-between shrink-0">
        <span>⛏ CONTROLS</span>
        <span className="text-g-muted text-[6px]">v2.0</span>
      </div>

      {/* ── Playback buttons ── */}
      <div className="px-3 pt-3 pb-2 grid grid-cols-2 gap-2 shrink-0"
           style={{ borderBottom: '1px solid #3d3020' }}>
        <button
          className={`game-btn ${isRunning ? 'game-btn-yellow' : 'game-btn-green'} text-[6px]`}
          onClick={isRunning ? controls.pause : controls.start}
        >
          {isRunning ? '⏸ PAUSE' : isPaused ? '▶ RESUME' : '▶ START'}
        </button>
        <button className="game-btn game-btn-red text-[6px]" onClick={controls.stop}>
          ■ STOP
        </button>
        <button
          className="game-btn game-btn-cyan text-[6px] col-span-2"
          onClick={() => controls.generateMine()}
        >
          🔄 NEW MINE
        </button>
      </div>

      {/* ── Scrollable param sections ── */}
      <div className="flex-1 overflow-y-auto">

        <Section icon="🚛" title="AGENTS">
          <Slider {...sp} emoji="🚛" label="Trucks"       section="simulation" keyName="num_trucks"   min={1}   max={10}   step={1}/>
          <Slider {...sp} emoji="👷" label="Workers"      section="simulation" keyName="num_workers"  min={1}   max={20}   step={1}/>
          <Slider {...sp} emoji="⚡" label="Truck Speed"  section="simulation" keyName="truck_speed"  min={2}   max={30}   step={1}/>
          <Slider {...sp} emoji="⏱" label="Tick Rate ms" section="simulation" keyName="tick_rate_ms" min={50}  max={1000} step={50}/>
        </Section>

        <Section icon="☣" title="HAZARD">
          <Slider {...sp} emoji="⚠" label="Hazard Thresh"  section="hazard" keyName="hazard_threshold"    min={0.1} max={0.95} step={0.05}/>
          <Slider {...sp} emoji="🚨" label="Evac Trigger"  section="hazard" keyName="evacuation_threshold" min={0.3} max={1.0}  step={0.05}/>
          <Slider {...sp} emoji="🔬" label="Hazard λ"      section="hazard" keyName="hazard_lambda"        min={0.5} max={8}    step={0.5}/>
          <Slider {...sp} emoji="💨" label="Base Gas"      section="hazard" keyName="gas_level_default"    min={0}   max={0.9}  step={0.05}/>
          <Slider {...sp} emoji="📳" label="Base Vibration" section="hazard" keyName="vibration_default"   min={0}   max={0.9}  step={0.05}/>
          <Slider {...sp} emoji="🎲" label="Emerge/tick"   section="hazard" keyName="hazard_emerge_chance" min={0}   max={0.15} step={0.005}/>
        </Section>

        <Section icon="📋" title="SCHEDULE (CSP)" defaultOpen={false}>
          <Slider {...sp} emoji="🕐" label="Time Slots"    section="schedule" keyName="num_time_slots"      min={4}  max={24} step={1}/>
          <Slider {...sp} emoji="⛏" label="Max Active"    section="schedule" keyName="processing_capacity" min={1}  max={8}  step={1}/>
          <Slider {...sp} emoji="💥" label="Blast Cooldown" section="schedule" keyName="blast_cooldown_slots" min={1} max={6}  step={1}/>
        </Section>

        <Section icon="🗺" title="MINE LAYOUT" defaultOpen={false}>
          <Slider {...sp} emoji="🔗" label="Junctions"    section="mine" keyName="num_junctions" min={5}   max={30}  step={1}/>
          <Slider {...sp} emoji="💎" label="Ore Zones"    section="mine" keyName="num_ore_zones" min={2}   max={10}  step={1}/>
          <Slider {...sp} emoji="🏠" label="Exits"        section="mine" keyName="num_exits"     min={1}   max={5}   step={1}/>
          <Slider {...sp} emoji="🕸" label="Connectivity" section="mine" keyName="connectivity"  min={0.1} max={0.9} step={0.05}/>
        </Section>
      </div>

      {/* ── Footer ── */}
      <div className="px-3 py-2 shrink-0 font-pixel text-[5px] text-g-dim leading-relaxed"
           style={{ borderTop: '1px solid #3d3020' }}>
        <div className="text-g-muted">A* · CSP/AC-3 · BAYESIAN</div>
        <div>WEBSOCKET LIVE STREAM</div>
      </div>
    </div>
  );
}
