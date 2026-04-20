import { useState, useEffect, useRef, useCallback } from 'react';
import { WS_URL } from '../utils/constants';

export function useWebSocket(onMessage) {
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState(null);
  const socketRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);

  const connect = useCallback(() => {
    if (socketRef.current?.readyState === WebSocket.OPEN) return;

    console.log("Connecting to WebSocket...");
    const socket = new WebSocket(WS_URL);

    socket.onopen = () => {
      console.log("WebSocket connected");
      setIsConnected(true);
      setError(null);
    };

    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (onMessage) onMessage(data);
      } catch (err) {
        console.error("Failed to parse WebSocket message:", err);
      }
    };

    socket.onerror = (err) => {
      console.error("WebSocket error:", err);
      setError("Connection error");
      setIsConnected(false);
    };

    socket.onclose = () => {
      console.log("WebSocket disconnected");
      setIsConnected(false);
      
      // Auto-reconnect after 3 seconds
      reconnectTimeoutRef.current = setTimeout(() => {
        connect();
      }, 3000);
    };

    socketRef.current = socket;
  }, [onMessage]);

  useEffect(() => {
    connect();
    return () => {
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      if (socketRef.current) {
        socketRef.current.onclose = null; // Prevent reconnect on intentional close
        socketRef.current.close();
      }
    };
  }, [connect]);

  const sendMessage = useCallback((data) => {
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify(data));
    }
  }, []);

  return { isConnected, error, sendMessage };
}
