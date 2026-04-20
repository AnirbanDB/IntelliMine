export const WS_URL = "ws://localhost:8000/ws/live-state";
export const API_BASE_URL = "http://localhost:8000/api";

export const AGENT_STATES = {
  IDLE: "idle",
  MOVING: "moving",
  LOADING: "loading",
  UNLOADING: "unloading",
  WORKING: "working",
  EVACUATING: "evacuating",
  WAITING: "waiting",
};

export const NODE_TYPES = {
  JUNCTION: "junction",
  ORE_ZONE: "ore_zone",
  EXIT: "exit",
};

export const HAZARD_TYPES = {
  GAS_LEAK: "gas_leak",
  COLLAPSE: "collapse",
  TOXIC: "toxic",
  FIRE: "fire",
  FLOOD: "flood",
};

export const ACTIVITY_COLORS = {
  blast: "bg-orange-500",
  drill: "bg-blue-500",
  load: "bg-green-500",
  idle: "bg-gray-500/20",
  halted: "bg-red-500",
};
