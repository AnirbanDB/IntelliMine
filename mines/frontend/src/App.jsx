import { useState, useCallback } from 'react';
import { useSimulation } from './hooks/useSimulation';
import MineMap from './components/MineMap';
import ControlPanel from './components/ControlPanel';
import HazardHUD from './components/HazardDashboard';
import ScheduleStrip from './components/ScheduleView';
import EventFeed from './components/EventLog';
import { AlertTriangle } from 'lucide-react';
import { simulationApi } from './utils/api';

/* ── Game-mode path challenge overlay ─────────────────────────────── */
function GameModePanel({ graph, onClose }) {
  const nodes = graph?.nodes || [];
  const exits = nodes.filter(n => n.type === 'exit');
  const ores  = nodes.filter(n => n.type === 'ore_zone');

  const [start, setStart]       = useState(exits[0]?.id || '');
  const [goal,  setGoal]        = useState(ores[0]?.id  || '');
  const [playerPath, setPath]   = useState([]);
  const [result,     setResult] = useState(null);
  const [phase, setPhase]       = useState('pick'); // 'pick' | 'result'

  const addNode = (id) => {
    if (!playerPath.length) {
      if (id !== start) return;
    }
    if (playerPath.includes(id)) return;
    setPath(p => [...p, id]);
  };

  const reset = () => { setPath([]); setResult(null); setPhase('pick'); };

  const submit = async () => {
    try {
      const res = await simulationApi.solvePath(start, goal, playerPath);
      setResult(res.data);
      setPhase('result');
    } catch (e) {
      console.error(e);
    }
  };

  const verdictColor = {
    OPTIMAL:  '#22dd55', GREAT: '#88ff44', GOOD: '#ffcc00',
    POOR: '#ff8800', TERRIBLE: '#ff2200', INVALID: '#ff0000',
  };

  return (
    <div className="absolute inset-0 z-50 flex items-center justify-center"
         style={{ background: 'rgba(4,3,2,0.92)' }}>
      <div className="game-panel-bright w-[560px] max-h-[85vh] overflow-y-auto">
        {/* Header */}
        <div className="game-header flex items-center justify-between">
          <span>🎮 PATH CHALLENGE — BEAT THE A* ALGORITHM</span>
          <button onClick={onClose} className="game-btn game-btn-red text-[6px] px-2 py-1">✕ EXIT</button>
        </div>

        <div className="p-4 space-y-4">
          {/* Instructions */}
          <div className="font-data text-[10px] text-g-muted p-3 border border-g-border/40"
               style={{ background: 'rgba(0,0,0,0.4)' }}>
            <div className="font-pixel text-[7px] text-g-ore mb-2">HOW TO PLAY:</div>
            <div>1. Choose a START exit and a GOAL ore zone.</div>
            <div>2. Click nodes on the map (left panel) to build your path.</div>
            <div>3. Submit — the AI reveals its optimal A* path and scores you.</div>
            <div className="mt-1 text-g-dim">Edge costs shown on tunnels = distance × gradient × condition</div>
          </div>

          {/* Start / Goal pickers */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <div className="font-pixel text-[6px] text-g-exit mb-1">🏠 START (EXIT)</div>
              <select value={start} onChange={e => { setStart(e.target.value); reset(); }}
                      className="w-full font-data text-[10px] text-g-text px-2 py-1"
                      style={{ background:'#1a1410', border:'1px solid #6b4c1e' }}>
                {exits.map(n => <option key={n.id} value={n.id}>{n.label||n.id}</option>)}
              </select>
            </div>
            <div>
              <div className="font-pixel text-[6px] text-g-ore mb-1">💎 GOAL (ORE ZONE)</div>
              <select value={goal} onChange={e => { setGoal(e.target.value); reset(); }}
                      className="w-full font-data text-[10px] text-g-text px-2 py-1"
                      style={{ background:'#1a1410', border:'1px solid #6b4c1e' }}>
                {ores.map(n => <option key={n.id} value={n.id}>{n.label||n.id}</option>)}
              </select>
            </div>
          </div>

          {/* Your path builder */}
          {phase === 'pick' && (
            <div>
              <div className="font-pixel text-[6px] text-g-muted mb-2">YOUR PATH ({playerPath.length} nodes):</div>
              <div className="flex flex-wrap gap-1 min-h-[28px] p-2 border border-g-border/30"
                   style={{ background: 'rgba(0,0,0,0.5)' }}>
                {playerPath.map((nid, i) => (
                  <span key={i} className="font-data text-[9px] px-1.5 py-0.5 border"
                        style={{ background:'rgba(0,180,100,0.15)', borderColor:'#22dd55', color:'#aaffcc' }}>
                    {nid}
                    {i < playerPath.length-1 && <span className="text-g-muted ml-1">→</span>}
                  </span>
                ))}
                {!playerPath.length && (
                  <span className="font-pixel text-[6px] text-g-dim italic">
                    Click nodes on the map to add them...
                  </span>
                )}
              </div>

              {/* Node picker grid */}
              <div className="mt-2">
                <div className="font-pixel text-[6px] text-g-muted mb-1">TAP A NODE TO ADD:</div>
                <div className="flex flex-wrap gap-1">
                  {nodes.map(n => {
                    const inPath = playerPath.includes(n.id);
                    const isStart = n.id === start;
                    const canAdd = !inPath && (playerPath.length === 0 ? isStart : true);
                    return (
                      <button key={n.id}
                              disabled={!canAdd}
                              onClick={() => addNode(n.id)}
                              className="font-data text-[8px] px-1.5 py-0.5 border transition-all"
                              style={{
                                background: inPath ? 'rgba(34,221,85,0.2)' : 'rgba(0,0,0,0.5)',
                                borderColor: n.type==='exit' ? '#22dd55' : n.type==='ore_zone' ? '#ffaa22' : '#5e6ad2',
                                color: canAdd ? '#f0e6cc' : '#3a3020',
                                cursor: canAdd ? 'pointer' : 'not-allowed',
                              }}>
                        {n.label||n.id}
                      </button>
                    );
                  })}
                </div>
              </div>

              <div className="flex gap-2 mt-3">
                <button onClick={reset} className="game-btn game-btn-yellow text-[6px] flex-1">🔄 RESET</button>
                <button
                  onClick={submit}
                  disabled={playerPath.length < 2 || playerPath[playerPath.length-1] !== goal}
                  className="game-btn game-btn-green text-[6px] flex-1"
                  style={{ opacity: (playerPath.length >= 2 && playerPath[playerPath.length-1] === goal) ? 1 : 0.4 }}>
                  ✓ SUBMIT PATH
                </button>
              </div>
              {playerPath.length >= 2 && playerPath[playerPath.length-1] !== goal && (
                <div className="font-pixel text-[6px] text-g-warn text-center mt-1">
                  Path must end at: {goal}
                </div>
              )}
            </div>
          )}

          {/* Result panel */}
          {phase === 'result' && result && (
            <div className="space-y-3">
              {/* Score */}
              <div className="text-center p-4 border-2"
                   style={{ borderColor: verdictColor[result.verdict] || '#888',
                            background: 'rgba(0,0,0,0.6)' }}>
                <div className="font-pixel text-[8px] text-g-muted mb-1">YOUR SCORE</div>
                <div className="font-pixel text-[28px]"
                     style={{ color: verdictColor[result.verdict], textShadow:`0 0 16px ${verdictColor[result.verdict]}` }}>
                  {result.score}
                </div>
                <div className="font-pixel text-[10px] mt-1"
                     style={{ color: verdictColor[result.verdict] }}>
                  {result.verdict}
                </div>
                <div className="font-data text-[9px] text-g-muted mt-1">
                  A* explored {result.nodes_explored} nodes
                </div>
              </div>

              {/* Side-by-side comparison */}
              <div className="grid grid-cols-2 gap-2">
                {/* Your path */}
                <div className="p-2 border" style={{ borderColor:'#5e6ad2', background:'rgba(0,0,0,0.5)' }}>
                  <div className="font-pixel text-[6px] text-g-muted mb-2">YOUR PATH</div>
                  <div className="font-pixel text-[9px] text-g-warn mb-1">
                    Cost: {result.player_cost === Infinity ? '∞ (invalid)' : result.player_cost.toFixed(1)}
                  </div>
                  {result.player_edges.map((e,i) => (
                    <div key={i} className="font-data text-[8px] text-g-muted flex justify-between">
                      <span>{e.from} → {e.to}</span>
                      <span className={e.invalid ? 'text-g-danger' : 'text-g-ore'}>
                        {e.invalid ? 'INVALID' : e.cost?.toFixed(1)}
                      </span>
                    </div>
                  ))}
                </div>
                {/* Optimal */}
                <div className="p-2 border" style={{ borderColor:'#22dd55', background:'rgba(0,0,0,0.5)' }}>
                  <div className="font-pixel text-[6px] text-g-exit mb-2">★ OPTIMAL (A*)</div>
                  <div className="font-pixel text-[9px] text-g-safe mb-1">
                    Cost: {result.optimal_cost.toFixed(1)}
                  </div>
                  {result.optimal_edges.map((e,i) => (
                    <div key={i} className="font-data text-[8px] text-g-muted flex justify-between">
                      <span>{e.from} → {e.to}</span>
                      <span className="text-g-exit">{e.cost?.toFixed(1)}</span>
                    </div>
                  ))}
                </div>
              </div>

              <button onClick={reset} className="game-btn game-btn-cyan text-[6px] w-full">
                🔄 PLAY AGAIN
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

/* ── Main App ──────────────────────────────────────────────────────── */
export default function App() {
  const { state, isConnected, error, controls } = useSimulation();
  const [showSchedule,  setShowSchedule]  = useState(false);
  const [showControls,  setShowControls]  = useState(true);
  const [blastEnabled,  setBlastEnabled]  = useState(true);
  const [gameMode,      setGameMode]      = useState(false);

  const isRunning = state.status === 'running';
  const tick = String(state.tick).padStart(5, '0');

  const toggleBlast = useCallback(() => {
    const next = !blastEnabled;
    setBlastEnabled(next);
    controls.updateParams({ schedule: { blast_enabled: next } });
  }, [blastEnabled, controls]);

  // Right panel width varies with schedule visibility
  const rightW = 'w-56';

  return (
    <div className="relative w-screen h-screen overflow-hidden bg-g-bg select-none">

      {/* ── Fullscreen mine map ── */}
      <div className="absolute inset-0">
        <MineMap
          graph={state.graph}
          trucks={state.trucks}
          workers={state.workers}
          active_hazards={state.active_hazards}
          paths={state.paths}
          isRunning={isRunning}
        />
      </div>

      {/* ══════════════════════════════════════════════
          TOP HUD
      ══════════════════════════════════════════════ */}
      <div className="absolute top-0 left-0 right-0 z-30 flex items-center gap-2 px-3 py-2"
           style={{ background: 'linear-gradient(to bottom, rgba(7,5,3,0.97) 70%, transparent)',
                    borderBottom: '1px solid rgba(107,76,30,0.3)' }}>

        <div className="font-pixel text-g-ore text-[8px] tracking-widest shrink-0"
             style={{ textShadow: '0 0 8px #ffaa22, 2px 2px 0 #2a1800' }}>
          ⛏ INTELLIMINE
        </div>

        <div className="hud-stat">
          <span className="hud-stat-label">TICK</span>
          <span className="hud-stat-value text-g-torch">{tick}</span>
        </div>
        <div className={`hud-stat font-pixel ${isRunning ? 'status-safe' : state.status==='paused' ? 'status-warn' : 'status-stopped'}`}>
          <span className="hud-stat-label">SIM</span>
          <span className="hud-stat-value" style={{fontSize:'6px'}}>
            {isRunning ? '▶ RUN' : state.status==='paused' ? '⏸' : '■ STOP'}
          </span>
        </div>
        <div className="hud-stat">
          <span className="hud-stat-label">🚛</span>
          <span className="hud-stat-value text-g-truck">{state.trucks.length}</span>
        </div>
        <div className="hud-stat">
          <span className="hud-stat-label">👷</span>
          <span className="hud-stat-value text-g-worker">{state.workers.length}</span>
        </div>
        <div className={`hud-stat ${state.active_hazards.length>0?'status-danger':'status-stopped'}`}>
          <span className="hud-stat-label">☣</span>
          <span className="hud-stat-value">{state.active_hazards.length}</span>
        </div>

        {/* Blast toggle */}
        <button
          onClick={toggleBlast}
          className={`font-pixel text-[6px] px-2 py-1 border transition-all ${
            blastEnabled
              ? 'border-orange-500/60 bg-orange-900/30 text-orange-300'
              : 'border-g-border/40 bg-black/30 text-g-muted'
          }`}
          title="Toggle blast operations in CSP schedule"
        >
          💥 BLAST {blastEnabled ? 'ON' : 'OFF'}
        </button>

        {/* WS status */}
        <div className={`font-pixel text-[6px] px-2 py-1 border ${
          isConnected ? 'text-g-exit border-g-exit/40 bg-g-exit/10' : 'text-g-danger border-g-danger/40 animate-pulse'
        }`}>
          {isConnected ? '● LIVE' : '✕ OFFLINE'}
        </div>

        <div className="flex-1"/>

        {/* Right-side toggles */}
        <button
          className={`game-btn text-[6px] px-2 py-1 ${gameMode ? 'game-btn-green' : 'game-btn-cyan'}`}
          onClick={() => setGameMode(v => !v)}
          disabled={blastEnabled}
          title={blastEnabled ? 'Disable blast first to enter game mode' : 'Enter path challenge'}
          style={{ opacity: blastEnabled ? 0.4 : 1 }}
        >
          🎮 {gameMode ? 'EXIT GAME' : 'GAME MODE'}
        </button>
        <button
          className={`game-btn text-[6px] px-2 py-1 ${showSchedule ? 'game-btn-yellow' : 'game-btn-cyan'}`}
          onClick={() => setShowSchedule(v => !v)}
        >
          📋 {showSchedule ? 'HIDE CSP' : 'SCHEDULE'}
        </button>
        <button
          className="game-btn game-btn-yellow text-[6px] px-2 py-1"
          onClick={() => setShowControls(v => !v)}
        >
          ⚙ {showControls ? 'HIDE' : 'CONTROLS'}
        </button>
      </div>

      {/* ══════════════════════════════════════════════
          LEFT PANEL — Controls
      ══════════════════════════════════════════════ */}
      {showControls && (
        <div className="absolute left-0 z-20 w-64 overflow-y-auto"
             style={{
               top: '52px',
               bottom: showSchedule ? '148px' : '0',
               background: 'linear-gradient(to right, rgba(7,5,3,0.97) 88%, transparent)',
               borderRight: '1px solid rgba(107,76,30,0.25)',
             }}>
          <ControlPanel state={state} controls={controls} blastEnabled={blastEnabled} />
        </div>
      )}

      {/* ══════════════════════════════════════════════
          RIGHT PANEL — Hazard + Events
      ══════════════════════════════════════════════ */}
      <div className={`absolute right-0 z-20 ${rightW} flex flex-col`}
           style={{
             top: '52px',
             bottom: showSchedule ? '148px' : '0',
             background: 'linear-gradient(to left, rgba(7,5,3,0.97) 88%, transparent)',
             borderLeft: '1px solid rgba(107,76,30,0.25)',
           }}>
        <div className="overflow-y-auto flex-1">
          <HazardHUD
            hazard_probabilities={state.hazard_probabilities}
            sensor_readings={state.sensor_readings}
            active_hazards={state.active_hazards}
          />
        </div>
        {/* Event feed — always visible at the bottom of right panel */}
        <div className="shrink-0" style={{ borderTop: '1px solid #3d3020' }}>
          <EventFeed events={state.events_log} />
        </div>
      </div>

      {/* ══════════════════════════════════════════════
          BOTTOM — CSP Schedule strip (toggleable)
          Adjusts left/right margins to not cover side panels
      ══════════════════════════════════════════════ */}
      {showSchedule && (
        <div className="absolute bottom-0 z-20"
             style={{
               left:  showControls ? '256px' : '0',
               right: '224px',
               background: 'rgba(7,5,3,0.98)',
               borderTop: '2px solid #6b4c1e',
             }}>
          <ScheduleStrip schedule={state.schedule} parameters={state.parameters} />
        </div>
      )}

      {/* ══════════════════════════════════════════════
          HAZARD ALERT BANNER
      ══════════════════════════════════════════════ */}
      {state.active_hazards.length > 0 && (
        <div className="absolute z-50 pointer-events-none
                        flex items-center gap-2 px-4 py-2 border-2 border-g-danger
                        font-pixel text-[7px] text-g-danger animate-danger-flash"
             style={{
               top: '58px',
               left: '50%', transform: 'translateX(-50%)',
               background: 'rgba(20,5,0,0.97)',
               boxShadow: '0 0 20px rgba(255,34,0,0.5)',
             }}>
          <AlertTriangle size={13} />
          ⚠ HAZARD — {state.active_hazards.length} ZONE{state.active_hazards.length>1?'S':''} AT RISK
          <AlertTriangle size={13} />
        </div>
      )}

      {error && (
        <div className="absolute top-16 left-1/2 -translate-x-1/2 z-50
                        font-pixel text-[7px] text-g-danger px-3 py-2 border-2 border-g-danger"
             style={{ background: 'rgba(30,0,0,0.97)' }}>
          ✕ {error} — CHECK BACKEND
        </div>
      )}

      {/* ══════════════════════════════════════════════
          GAME MODE OVERLAY
      ══════════════════════════════════════════════ */}
      {gameMode && !blastEnabled && (
        <GameModePanel graph={state.graph} onClose={() => setGameMode(false)} />
      )}
    </div>
  );
}
