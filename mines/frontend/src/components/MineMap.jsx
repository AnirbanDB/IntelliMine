import { useMemo, useRef, useState, useCallback, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

// ── Stable offsets so clustered agents don't jitter ───────────────────
function useStableOffsets(agents) {
  const ref = useRef({});
  agents.forEach((a) => {
    if (!ref.current[a.id]) {
      ref.current[a.id] = {
        dx: (Math.random() - 0.5) * 22,
        dy: (Math.random() - 0.5) * 22,
      };
    }
  });
  return ref.current;
}

// ── Interpolate agent position between nodes ──────────────────────────
function agentPos(agent, nodeMap) {
  const moving = agent.state === 'moving' || agent.state === 'evacuating';
  if (moving && agent.path?.length > 1 && agent.path_index < agent.path.length - 1) {
    const a = nodeMap[agent.path[agent.path_index]];
    const b = nodeMap[agent.path[agent.path_index + 1]];
    if (a && b) {
      const t = Math.min(1, Math.max(0, agent.progress ?? 0));
      return { x: a.x + (b.x - a.x) * t, y: a.y + (b.y - a.y) * t };
    }
  }
  const cur = nodeMap[agent.current_node];
  return cur ? { x: cur.x, y: cur.y } : { x: 0, y: 0 };
}

// ── SVG <defs> — gradients, filters, patterns ─────────────────────────
function MapDefs() {
  return (
    <defs>
      {/* Stone floor tile */}
      <pattern id="p-stone" patternUnits="userSpaceOnUse" width="48" height="48">
        <rect width="48" height="48" fill="#0e0c09"/>
        <rect x="0"  y="0"  width="24" height="24" fill="#111009" opacity="0.55"/>
        <rect x="24" y="24" width="24" height="24" fill="#13110a" opacity="0.45"/>
        <rect x="24" y="0"  width="24" height="24" fill="#0c0b08" opacity="0.35"/>
        <line x1="0" y1="24" x2="48" y2="24" stroke="#1c1911" strokeWidth="0.6"/>
        <line x1="24" y1="0" x2="24" y2="48" stroke="#1c1911" strokeWidth="0.6"/>
        <circle cx="6"  cy="9"  r="1.8" fill="#1a1810"/>
        <circle cx="38" cy="14" r="1.2" fill="#1a1810"/>
        <circle cx="18" cy="37" r="2.2" fill="#141209"/>
        <circle cx="42" cy="40" r="1"   fill="#1a1810"/>
        <circle cx="30" cy="6"  r="1.5" fill="#1a1810"/>
      </pattern>

      {/* Dirt strip at surface */}
      <pattern id="p-dirt" patternUnits="userSpaceOnUse" width="20" height="10">
        <rect width="20" height="10" fill="#3d280a"/>
        <rect x="1" y="1" width="6"  height="4" fill="#4d3310" opacity="0.5"/>
        <rect x="12" y="4" width="5" height="3" fill="#2e1e07" opacity="0.4"/>
      </pattern>

      {/* Tunnel carved-out bg */}
      <linearGradient id="g-tunnel" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%"   stopColor="#1a1610"/>
        <stop offset="100%" stopColor="#100e09"/>
      </linearGradient>

      {/* Ore gold glow */}
      <radialGradient id="g-ore" cx="50%" cy="50%" r="50%">
        <stop offset="0%"   stopColor="#ffcc00" stopOpacity="0.6"/>
        <stop offset="60%"  stopColor="#ff8800" stopOpacity="0.25"/>
        <stop offset="100%" stopColor="#ff4400" stopOpacity="0"/>
      </radialGradient>

      {/* Lava / hazard glow */}
      <radialGradient id="g-lava" cx="50%" cy="50%" r="50%">
        <stop offset="0%"   stopColor="#ff4400" stopOpacity="0.7"/>
        <stop offset="70%"  stopColor="#cc1100" stopOpacity="0.3"/>
        <stop offset="100%" stopColor="#ff0000" stopOpacity="0"/>
      </radialGradient>

      {/* Exit surface glow */}
      <radialGradient id="g-exit" cx="50%" cy="50%" r="50%">
        <stop offset="0%"   stopColor="#22ff66" stopOpacity="0.4"/>
        <stop offset="100%" stopColor="#00cc44" stopOpacity="0"/>
      </radialGradient>

      {/* Torch flame gradient */}
      <radialGradient id="g-torch" cx="50%" cy="70%" r="60%">
        <stop offset="0%"   stopColor="#ffffff" stopOpacity="0.9"/>
        <stop offset="40%"  stopColor="#ffcc44" stopOpacity="0.8"/>
        <stop offset="100%" stopColor="#ff6600" stopOpacity="0"/>
      </radialGradient>

      {/* Soft glow filter */}
      <filter id="f-glow" x="-60%" y="-60%" width="220%" height="220%">
        <feGaussianBlur stdDeviation="4" result="b"/>
        <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
      </filter>
      <filter id="f-glow-lg" x="-100%" y="-100%" width="300%" height="300%">
        <feGaussianBlur stdDeviation="8" result="b"/>
        <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
      </filter>
      <filter id="f-shadow">
        <feDropShadow dx="1" dy="1.5" stdDeviation="1.5" floodColor="#000" floodOpacity="0.9"/>
      </filter>

      {/* Path arrow */}
      <marker id="m-arrow" markerWidth="7" markerHeight="5" refX="12" refY="2.5" orient="auto">
        <polygon points="0 0,7 2.5,0 5" fill="#00ddff" opacity="0.7"/>
      </marker>
    </defs>
  );
}

// ── Torch flame (SVG, no emoji) ───────────────────────────────────────
function Torch({ x, y }) {
  return (
    <g transform={`translate(${x},${y})`}>
      {/* stick */}
      <rect x="-2" y="2" width="4" height="9" rx="1" fill="#6b3a10"/>
      {/* flame halo */}
      <ellipse cx="0" cy="-3" rx="5" ry="7" fill="url(#g-torch)" filter="url(#f-glow)" opacity="0.85"
               style={{ animation: 'torchFlicker 0.13s ease-in-out infinite alternate' }}/>
      {/* flame core */}
      <ellipse cx="0" cy="-2" rx="2.5" ry="4" fill="#ffee88" opacity="0.9"/>
    </g>
  );
}

// ── Top-down cartoon truck (pure SVG) ────────────────────────────────
function Truck({ truck }) {
  const isLoading   = truck.state === 'loading';
  const isUnloading = truck.state === 'unloading';
  const isWaiting   = truck.state === 'waiting';
  const cargo    = truck.cargo    ?? 0;
  const maxCargo = truck.max_cargo ?? 100;
  const cargoFrac = maxCargo > 0 ? Math.min(1, cargo / maxCargo) : 0;
  const bodyColor = isWaiting ? '#3a6070' : '#00bbdd';
  const num = truck.id.replace('truck_', '');

  return (
    <g filter="url(#f-shadow)">
      {/* ── Shadow under truck ── */}
      <ellipse cx="0" cy="11" rx="14" ry="4" fill="#000" opacity="0.4"/>

      {/* ── Main body ── */}
      <rect x="-13" y="-9" width="26" height="18" rx="3"
            fill={bodyColor} stroke="#004455" strokeWidth="1.2"/>

      {/* ── Cab (front, top of view) ── */}
      <rect x="-10" y="-9" width="20" height="8" rx="2"
            fill={isWaiting ? '#2a4a58' : '#00ddf5'} stroke="#003344" strokeWidth="1"/>
      {/* Windshield */}
      <rect x="-7"  y="-8" width="14" height="5" rx="1" fill="#001820" opacity="0.6"/>
      {/* Windshield glare */}
      <rect x="-6"  y="-7.5" width="5" height="2" rx="0.5" fill="#ffffff" opacity="0.3"/>

      {/* ── Cargo bed (back) ── */}
      <rect x="-10" y="1" width="20" height="7" rx="1"
            fill="#003344" stroke="#002233" strokeWidth="0.8"/>
      {/* Cargo fill */}
      {cargoFrac > 0 && (
        <rect x="-9" y="2" width={Math.round(18 * cargoFrac)} height="5"
              rx="0.5" fill="#ffaa22" opacity="0.9"
              filter={cargoFrac > 0.8 ? 'url(#f-glow)' : undefined}/>
      )}

      {/* ── Wheels (4 corners) ── */}
      {[[-11,-7],[9,-7],[-11,5],[9,5]].map(([wx,wy],i) => (
        <g key={i}>
          <rect x={wx} y={wy} width="5" height="5" rx="1.2"
                fill="#111" stroke="#444" strokeWidth="0.7"/>
          <rect x={wx+1.2} y={wy+1.2} width="2.6" height="2.6" rx="0.6" fill="#333"/>
        </g>
      ))}

      {/* ── Truck ID ── */}
      <text y="-1.5" textAnchor="middle"
            fill={isWaiting ? '#88bbcc' : '#001820'}
            fontSize="6.5" fontFamily="'Press Start 2P',monospace" fontWeight="bold">
        T{num}
      </text>

      {/* ── State indicator ── */}
      {(isLoading || isUnloading) && (
        <g>
          <circle cx="0" cy="-17" r="6" fill={isLoading ? '#cc8800' : '#006644'} opacity="0.9"/>
          <text y="-14" textAnchor="middle" fill="white" fontSize="7" fontWeight="bold">
            {isLoading ? '⛏' : '↑'}
          </text>
        </g>
      )}
    </g>
  );
}

// ── Pixel-person worker (pure SVG) ────────────────────────────────────
function Worker({ worker }) {
  const isEvac = worker.state === 'evacuating';
  const skinCol  = isEvac ? '#dd8866' : '#f0c870';
  const bodyCol  = isEvac ? '#aa1100' : '#5a3a20';
  const helmCol  = isEvac ? '#cc2200' : '#e8a020';

  return (
    <g filter="url(#f-shadow)">
      {/* Shadow */}
      <ellipse cx="0" cy="14" rx="7" ry="2.5" fill="#000" opacity="0.35"/>

      {/* Legs */}
      <rect x="-5" y="8"  width="4" height="7" rx="1" fill={isEvac ? '#880000' : '#3a2010'}/>
      <rect x="1"  y="8"  width="4" height="7" rx="1" fill={isEvac ? '#880000' : '#3a2010'}/>

      {/* Body */}
      <rect x="-6" y="-1" width="12" height="10" rx="1.5"
            fill={bodyCol} stroke={isEvac ? '#ff4422' : '#3a2010'} strokeWidth="0.8"/>
      {/* Belt buckle */}
      <rect x="-2" y="6" width="4" height="2" rx="0.5" fill="#cc9900" opacity={isEvac?0:0.8}/>

      {/* Arms */}
      <rect x="-10" y="0"  width="5" height="3" rx="1" fill={bodyCol}/>
      <rect x="5"   y="0"  width="5" height="3" rx="1" fill={bodyCol}/>
      {/* Hands */}
      <circle cx="-9" cy="3"  r="2.2" fill={skinCol}/>
      <circle cx="9"  cy="3"  r="2.2" fill={skinCol}/>

      {/* Head */}
      <circle cx="0" cy="-6" r="6" fill={skinCol} stroke="#d4a050" strokeWidth="0.6"/>
      {/* Eyes */}
      <circle cx="-2.2" cy="-6.5" r="1.1" fill={isEvac ? '#ff4422' : '#2a1a08'}/>
      <circle cx="2.2"  cy="-6.5" r="1.1" fill={isEvac ? '#ff4422' : '#2a1a08'}/>
      {/* Mouth (smile or frown) */}
      {isEvac
        ? <path d="M-2.5,-3.5 Q0,-2 2.5,-3.5" stroke="#cc2200" strokeWidth="0.8" fill="none"/>
        : <path d="M-2,-3.5 Q0,-4.5 2,-3.5" stroke="#8a5020" strokeWidth="0.8" fill="none"/>}

      {/* Helmet */}
      <rect x="-6" y="-13" width="12" height="7" rx="3"
            fill={helmCol} stroke={isEvac ? '#ff6644' : '#c08010'} strokeWidth="0.8"/>
      {/* Helmet brim */}
      <rect x="-7" y="-8" width="14" height="2" rx="0.5" fill={helmCol} opacity="0.8"/>
      {/* Helmet lamp */}
      <circle cx="5" cy="-11" r="2.8" fill="#ffee44"
              filter="url(#f-glow)"
              style={{ animation: 'torchFlicker 0.15s ease-in-out infinite alternate' }}/>
      <circle cx="5" cy="-11" r="1.4" fill="#ffffff" opacity="0.9"/>

      {/* Evacuation "!" */}
      {isEvac && (
        <g style={{ animation: 'fire-float 0.8s ease-out infinite' }}>
          <text y="-22" textAnchor="middle" fill="#ff2200"
                fontSize="10" fontFamily="'Press Start 2P',monospace" fontWeight="bold"
                filter="url(#f-glow-lg)">!</text>
        </g>
      )}
    </g>
  );
}

// ── Main MineMap component ────────────────────────────────────────────
export default function MineMap({
  graph,
  trucks = [],
  workers = [],
  active_hazards = [],
  paths = [],
  isRunning = false,
}) {
  const { nodes = [], edges = [] } = graph || {};
  const workerOffsets = useStableOffsets(workers);

  // ── Zoom / pan state ──────────────────────────────────────────────
  const [view, setView] = useState({ x: 0, y: 0, scale: 1 });
  const isDragging   = useRef(false);
  const dragStart    = useRef({ mx: 0, my: 0, vx: 0, vy: 0 });
  const svgRef       = useRef(null);

  const clampScale = (s) => Math.min(4.0, Math.max(0.25, s));

  const handleWheel = useCallback((e) => {
    e.preventDefault();
    const svg = svgRef.current;
    if (!svg) return;
    const rect = svg.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;
    const factor = e.deltaY < 0 ? 1.12 : 0.89;
    setView(v => {
      const newScale = clampScale(v.scale * factor);
      const ratio = newScale / v.scale;
      return {
        scale: newScale,
        x: mx - ratio * (mx - v.x),
        y: my - ratio * (my - v.y),
      };
    });
  }, []);

  const handleMouseDown = useCallback((e) => {
    if (e.button !== 0) return;
    isDragging.current = true;
    dragStart.current = { mx: e.clientX, my: e.clientY, vx: view.x, vy: view.y };
    e.currentTarget.style.cursor = 'grabbing';
  }, [view]);

  const handleMouseMove = useCallback((e) => {
    if (!isDragging.current) return;
    const dx = e.clientX - dragStart.current.mx;
    const dy = e.clientY - dragStart.current.my;
    setView(v => ({ ...v, x: dragStart.current.vx + dx, y: dragStart.current.vy + dy }));
  }, []);

  const handleMouseUp = useCallback((e) => {
    isDragging.current = false;
    if (e.currentTarget) e.currentTarget.style.cursor = 'grab';
  }, []);

  // Attach wheel with passive:false
  useEffect(() => {
    const el = svgRef.current;
    if (!el) return;
    el.addEventListener('wheel', handleWheel, { passive: false });
    return () => el.removeEventListener('wheel', handleWheel);
  }, [handleWheel]);

  const resetView = () => setView({ x: 0, y: 0, scale: 1 });
  const zoomIn    = () => setView(v => ({ ...v, scale: clampScale(v.scale * 1.2) }));
  const zoomOut   = () => setView(v => ({ ...v, scale: clampScale(v.scale * 0.83) }));

  // ── Derived data ──────────────────────────────────────────────────
  const viewBox = useMemo(() => {
    if (!nodes.length) return '0 0 900 640';
    const xs = nodes.map(n => n.x), ys = nodes.map(n => n.y);
    const pad = 70;
    return `${Math.min(...xs)-pad} ${Math.min(...ys)-pad} ${Math.max(...xs)-Math.min(...xs)+pad*2+30} ${Math.max(...ys)-Math.min(...ys)+pad*2+30}`;
  }, [nodes]);

  const [vbX, vbY, vbW, vbH] = viewBox.split(' ').map(Number);

  const nodeMap = useMemo(() => Object.fromEntries(nodes.map(n => [n.id, n])), [nodes]);

  const pathEdges = useMemo(() => {
    const s = new Set();
    paths.forEach(p => {
      for (let i = 0; i < p.path.length - 1; i++) s.add(`${p.path[i]}→${p.path[i+1]}`);
    });
    return s;
  }, [paths]);

  const hazardIds = useMemo(() => new Set(active_hazards.map(h => h.node_id)), [active_hazards]);

  // Torch positions: one per junction, offset slightly
  const torches = useMemo(() =>
    nodes.filter(n => n.type === 'junction').map(n => ({ x: n.x + 20, y: n.y - 12 })),
  [nodes]);

  const transform = `translate(${view.x},${view.y}) scale(${view.scale})`;

  return (
    <div className="relative w-full h-full overflow-hidden mine-map-container"
         style={{
           background: '#0e0c09',
           backgroundImage: `repeating-linear-gradient(0deg,transparent,transparent 47px,rgba(26,22,16,0.5) 47px,rgba(26,22,16,0.5) 48px),
                             repeating-linear-gradient(90deg,transparent,transparent 47px,rgba(26,22,16,0.5) 47px,rgba(26,22,16,0.5) 48px)`,
         }}>

      {/* ── SVG canvas ── */}
      <svg
        ref={svgRef}
        viewBox={viewBox}
        className="w-full h-full svg-pannable"
        preserveAspectRatio="xMidYMid meet"
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        style={{ cursor: isDragging.current ? 'grabbing' : 'grab' }}
      >
        <MapDefs />

        <g transform={transform}>
          {/* ── Stone background ── */}
          <rect x={vbX} y={vbY} width={vbW} height={vbH} fill="url(#p-stone)"/>

          {/* ── Depth vignette ── */}
          <defs>
            <linearGradient id="g-depth" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%"   stopColor="#000" stopOpacity="0"/>
              <stop offset="100%" stopColor="#000" stopOpacity="0.4"/>
            </linearGradient>
          </defs>
          <rect x={vbX} y={vbY} width={vbW} height={vbH} fill="url(#g-depth)"/>

          {/* ── Surface dirt + grass ── */}
          <rect x={vbX} y={vbY} width={vbW} height={30} fill="url(#p-dirt)"/>
          <rect x={vbX} y={vbY} width={vbW} height={6}  fill="#1e5c0a" opacity="0.95"/>

          {/* ── Ambient torch glow pools ── */}
          {torches.map((t, i) => (
            <ellipse key={i} cx={t.x} cy={t.y+18} rx={40} ry={28} fill="#ffaa22" opacity="0.03"/>
          ))}

          {/* ══════════════════════════════
              TUNNELS (drawn behind nodes)
          ══════════════════════════════ */}
          <g>
            {edges.map((edge, i) => {
              const s = nodeMap[edge.source], e2 = nodeMap[edge.target];
              if (!s || !e2) return null;
              const isPath = pathEdges.has(`${edge.source}→${edge.target}`);
              // midpoint for cost label
              const mx = (s.x + e2.x) / 2;
              const my = (s.y + e2.y) / 2;
              // edge cost (weight = distance × gradient × condition)
              const cost = edge.weight != null ? edge.weight : (edge.distance ?? 0);
              const costStr = cost > 999 ? `${(cost/1000).toFixed(1)}k` : Math.round(cost).toString();

              return (
                <g key={i}>
                  {/* Carved void */}
                  <line x1={s.x} y1={s.y} x2={e2.x} y2={e2.y}
                        stroke="#080604" strokeWidth={isPath ? 22 : 17} strokeLinecap="round"/>
                  {/* Stone wall shading */}
                  <line x1={s.x} y1={s.y} x2={e2.x} y2={e2.y}
                        stroke="#1a1610" strokeWidth={isPath ? 18 : 13} strokeLinecap="round"/>
                  {/* Tunnel floor */}
                  <line x1={s.x} y1={s.y} x2={e2.x} y2={e2.y}
                        stroke={isPath ? '#2e2618' : '#222018'} strokeWidth={isPath ? 13 : 10}
                        strokeLinecap="round"/>
                  {/* Rail ties */}
                  <line x1={s.x} y1={s.y} x2={e2.x} y2={e2.y}
                        stroke="#4a3e28" strokeWidth="1.5"
                        strokeDasharray="4 7" opacity="0.6"/>
                  {/* Active path: marching-ant cyan rail */}
                  {isPath && (
                    <>
                      <line x1={s.x} y1={s.y} x2={e2.x} y2={e2.y}
                            stroke="#0088bb" strokeWidth="3"
                            strokeDasharray="8 5" opacity="0.5"
                            markerEnd="url(#m-arrow)"/>
                      <line x1={s.x} y1={s.y} x2={e2.x} y2={e2.y}
                            stroke="#00ddff" strokeWidth="2"
                            strokeDasharray="6 9"
                            className="path-march" opacity="0.8"/>
                    </>
                  )}
                  {/* ── Cost label at midpoint ── */}
                  <rect x={mx - 11} y={my - 7} width={22} height={12} rx="2"
                        fill={isPath ? 'rgba(0,40,50,0.92)' : 'rgba(15,12,7,0.85)'}
                        stroke={isPath ? '#00aacc' : '#3d3020'}
                        strokeWidth="0.8"/>
                  <text x={mx} y={my + 3.5}
                        textAnchor="middle"
                        fill={isPath ? '#00ddff' : '#8a7050'}
                        fontSize="7"
                        fontFamily="'Press Start 2P', monospace"
                        fontWeight={isPath ? 'bold' : 'normal'}>
                    {costStr}
                  </text>
                </g>
              );
            })}
          </g>

          {/* ── Torches ── */}
          {torches.map((t, i) => <Torch key={i} x={t.x} y={t.y}/>)}

          {/* ══════════════════════════════
              NODES
          ══════════════════════════════ */}
          <g>
            {nodes.map(node => {
              const hp = node.hazard_probability ?? 0;
              const isHazard = hp > 0.5;
              const isActive = hazardIds.has(node.id);
              const isExit   = node.type === 'exit';
              const isOre    = node.type === 'ore_zone';

              const NR = 20; // node half-size
              const bg     = isHazard ? '#3a0600' : isExit ? '#0e3d1c' : isOre ? '#4a2c00' : '#1c1a3a';
              const border = isHazard ? '#ff3300' : isExit ? '#22dd55' : isOre ? '#ffaa22' : '#5e6ad2';
              const icon   = isHazard ? '☣' : isExit ? '🏠' : isOre ? '💎' : '🔦';

              return (
                <g key={node.id}>
                  {/* Glow pools */}
                  {isExit && <ellipse cx={node.x} cy={node.y} rx={50} ry={36} fill="url(#g-exit)" opacity="0.9"/>}
                  {isOre && !isHazard && (
                    <>
                      <ellipse cx={node.x} cy={node.y} rx={44} ry={32}
                               fill="url(#g-ore)" className="ore-glow"/>
                    </>
                  )}
                  {isHazard && (
                    <ellipse cx={node.x} cy={node.y}
                             rx={46 + hp * 22} ry={34 + hp * 18}
                             fill="url(#g-lava)"
                             className={isActive ? 'hazard-pulse' : ''}/>
                  )}

                  {/* Node body */}
                  <rect x={node.x - NR} y={node.y - NR}
                        width={NR * 2} height={NR * 2} rx="4"
                        fill={bg}
                        stroke={border} strokeWidth={isHazard ? 2.5 : isOre ? 2 : 1.5}
                        filter={isHazard ? 'url(#f-glow-lg)' : (isOre || isExit) ? 'url(#f-glow)' : undefined}/>

                  {/* Hazard heat fill */}
                  {hp > 0.2 && (
                    <rect x={node.x - NR} y={node.y - NR} width={NR*2} height={NR*2} rx="4"
                          fill={`rgba(255,60,0,${(hp * 0.5).toFixed(2)})`}/>
                  )}

                  {/* Icon */}
                  <text x={node.x} y={node.y + 6} textAnchor="middle" fontSize="16"
                        filter="url(#f-shadow)">
                    {icon}
                  </text>

                  {/* Label */}
                  <text x={node.x} y={node.y - NR - 7}
                        textAnchor="middle"
                        fill={isHazard ? '#ff9966' : isExit ? '#aaffcc' : isOre ? '#ffe080' : '#aaaadd'}
                        fontSize="8.5"
                        fontFamily="'Share Tech Mono', monospace"
                        fontWeight="bold"
                        filter="url(#f-shadow)">
                    {(node.label || node.id).toUpperCase()}
                  </text>

                  {/* Hazard % badge */}
                  {hp > 0.1 && (
                    <text x={node.x} y={node.y + NR + 13}
                          textAnchor="middle"
                          fill={hp > 0.6 ? '#ff4422' : '#ffaa00'}
                          fontSize="8"
                          fontFamily="'Press Start 2P', monospace"
                          filter={hp > 0.6 ? 'url(#f-glow)' : undefined}>
                      {(hp * 100).toFixed(0)}%
                    </text>
                  )}
                </g>
              );
            })}
          </g>

          {/* ══════════════════════════════
              TRUCKS (top-down cartoon)
          ══════════════════════════════ */}
          <AnimatePresence>
            {trucks.map(truck => {
              const { x, y } = agentPos(truck, nodeMap);
              return (
                <motion.g key={truck.id}
                  animate={{ x, y }}
                  transition={{ type: 'spring', damping: 26, stiffness: 70, mass: 1 }}>
                  <Truck truck={truck}/>
                </motion.g>
              );
            })}
          </AnimatePresence>

          {/* ══════════════════════════════
              WORKERS (pixel person)
          ══════════════════════════════ */}
          <AnimatePresence>
            {workers.map(worker => {
              const base = agentPos(worker, nodeMap);
              const off  = workerOffsets[worker.id] || { dx: 0, dy: 0 };
              const isEvac = worker.state === 'evacuating';
              const x = base.x + (isEvac ? 0 : off.dx);
              const y = base.y + (isEvac ? 0 : off.dy);
              return (
                <motion.g key={worker.id}
                  animate={{ x, y }}
                  transition={{ type: 'spring', damping: 30, stiffness: 85 }}>
                  <Worker worker={worker}/>
                </motion.g>
              );
            })}
          </AnimatePresence>
        </g>
      </svg>

      {/* ══════════════════════════════
          ZOOM CONTROLS (bottom-left, away from right panel)
      ══════════════════════════════ */}
      <div className="absolute bottom-4 left-4 flex items-center gap-1 z-30"
           style={{ background: 'rgba(10,8,5,0.9)', border: '1px solid #6b4c1e', padding: '4px 6px' }}>
        <button onClick={zoomOut}
                className="font-pixel text-g-ore text-[10px] w-6 h-6 flex items-center justify-center
                           hover:bg-white/10 transition-colors border border-g-border/40">
          −
        </button>
        <span className="font-pixel text-[7px] text-g-muted w-12 text-center">
          {Math.round(view.scale * 100)}%
        </span>
        <button onClick={zoomIn}
                className="font-pixel text-g-ore text-[10px] w-6 h-6 flex items-center justify-center
                           hover:bg-white/10 transition-colors border border-g-border/40">
          +
        </button>
        <button onClick={resetView}
                className="font-pixel text-[6px] text-g-muted px-1.5 h-6 ml-1
                           hover:text-g-ore hover:bg-white/5 transition-colors border border-g-border/30">
          RESET
        </button>
      </div>

      {/* ── Legend ── */}
      <div className="absolute top-2 left-2 z-30 flex gap-3 pointer-events-none"
           style={{ background: 'rgba(8,6,4,0.82)', border: '1px solid #3d3020', padding: '4px 8px' }}>
        {[
          { col: '#22dd55', label: 'EXIT' },
          { col: '#ffaa22', label: 'ORE' },
          { col: '#5e6ad2', label: 'JUNCTION' },
          { col: '#00ddff', label: 'TRUCK' },
          { col: '#f0e6cc', label: 'WORKER' },
          { col: '#ff3300', label: 'HAZARD' },
        ].map(({ col, label }) => (
          <div key={label} className="flex items-center gap-1">
            <div className="w-2.5 h-2.5 rounded-sm shrink-0" style={{ background: col }}/>
            <span className="font-pixel text-[5.5px]" style={{ color: col }}>{label}</span>
          </div>
        ))}
        <span className="font-pixel text-[5px] text-g-dim ml-1">SCROLL=ZOOM · DRAG=PAN</span>
      </div>
    </div>
  );
}
