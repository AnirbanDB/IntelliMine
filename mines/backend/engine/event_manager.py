"""
Event Manager Model for the Simulation Engine.

Manages the event queue for discrete events like blast completion,
hazard emergence, and truck arrivals.
"""
import heapq
from typing import List, Callable, Any, Dict
from dataclasses import dataclass, field

from models.hazards import HazardType

@dataclass(order=True)
class SimEvent:
    """A discrete event in the simulation."""
    tick: int
    event_type: str = field(compare=False)
    payload: Dict[str, Any] = field(default_factory=dict, compare=False)
    
class EventManager:
    def __init__(self):
        self.events: List[SimEvent] = []
        self.listeners: Dict[str, List[Callable]] = {}
        
    def schedule_event(self, tick: int, event_type: str, payload: Dict[str, Any] = None):
        """Schedule an event for a future tick."""
        if payload is None:
            payload = {}
        event = SimEvent(tick, event_type, payload)
        heapq.heappush(self.events, event)
        
    def add_listener(self, event_type: str, callback: Callable[[Dict[str, Any]], None]):
        """Register a callback for an event type."""
        if event_type not in self.listeners:
            self.listeners[event_type] = []
        self.listeners[event_type].append(callback)
        
    def process_events(self, current_tick: int):
        """Process all events up to the current tick."""
        processed_count = 0
        while self.events and self.events[0].tick <= current_tick:
            event = heapq.heappop(self.events)
            self._dispatch(event)
            processed_count += 1
        return processed_count
            
    def _dispatch(self, event: SimEvent):
        """Dispatch an event to its listeners."""
        # Special catch-all or specific handlers could be implemented here
        if event.event_type in self.listeners:
            for callback in self.listeners[event.event_type]:
                callback(event.payload)
                
    def clear(self):
        self.events = []
