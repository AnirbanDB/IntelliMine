import { useState, useCallback, useMemo } from 'react';
import { useWebSocket } from './useWebSocket';
import { simulationApi } from '../utils/api';

const DEFAULT_STATE = {
  tick: 0,
  status: 'stopped',
  graph: { nodes: [], edges: [] },
  trucks: [],
  workers: [],
  equipment: [],
  active_hazards: [],
  sensor_readings: {},
  hazard_probabilities: {},
  schedule: [],
  paths: [],
  events_log: [],
  parameters: {},
};

export function useSimulation() {
  const [state, setState] = useState(DEFAULT_STATE);

  const onMessage = useCallback((data) => {
    // Guard: make sure graph always has nodes/edges arrays
    if (data.graph && !data.graph.nodes)  data.graph.nodes = [];
    if (data.graph && !data.graph.edges)  data.graph.edges = [];
    setState(data);
  }, []);

  const { isConnected, error, sendMessage } = useWebSocket(onMessage);

  const controls = useMemo(() => ({
    start:        ()       => simulationApi.runSimulation('start'),
    pause:        ()       => simulationApi.runSimulation('pause'),
    stop:         ()       => simulationApi.runSimulation('stop'),
    generateMine: (seed)   => simulationApi.generateMine(seed),
    updateParams: (params) => simulationApi.updateParameters(params),
  }), []);

  return { state, isConnected, error, controls, sendMessage };
}
