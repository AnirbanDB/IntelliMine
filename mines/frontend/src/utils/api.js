import axios from 'axios';
import { API_BASE_URL } from './constants';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: { 'Content-Type': 'application/json' },
});

export const simulationApi = {
  /** Generate a new mine graph. seed is optional. */
  generateMine: (seed = null) =>
    api.post('/generate-mine', { seed }),

  /** Control simulation state: 'start' | 'pause' | 'stop' */
  runSimulation: (action) =>
    api.post('/run-simulation', { action }),

  /** Deep-merge params into simulation config.
   *  e.g. { simulation: { num_trucks: 5 }, hazard: { hazard_threshold: 0.7 } }
   */
  updateParameters: (params) =>
    api.post('/update-parameters', { params }),

  getSimulationState: () =>
    api.get('/simulation-state'),

  /** Run A* on the current mine graph */
  computePath: (start, goal, mode = 'hazard') =>
    api.post('/compute-path', { start, goal, mode }),

  /** Run CSP scheduler */
  computeSchedule: (zones = null, num_slots = 12) =>
    api.post('/compute-schedule', { zones, num_slots }),

  /** Run Bayesian inference */
  computeHazard: (evidence) =>
    api.post('/compute-hazard', { evidence }),

  /** Game mode: evaluate player path vs optimal A* path */
  solvePath: (start, goal, player_path) =>
    api.post('/solve-path', { start, goal, player_path }),
};

export default api;
