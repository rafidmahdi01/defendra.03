import { useEffect, useState } from "react";

const WS_URL = import.meta.env.VITE_WS_URL || "ws://127.0.0.1:8000/ws/dashboard";

export function useRealtime(onEvent) {
  const [connected, setConnected] = useState(false);
  const [events, setEvents] = useState([]);

  useEffect(() => {
    const socket = new WebSocket(WS_URL);
    socket.onopen = () => setConnected(true);
    socket.onclose = () => setConnected(false);
    socket.onmessage = (message) => {
      const payload = JSON.parse(message.data);
      setEvents((current) => [payload, ...current].slice(0, 25));
      onEvent?.(payload);
    };
    return () => socket.close();
  }, [onEvent]);

  return { connected, events };
}
