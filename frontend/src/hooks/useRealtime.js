import { useEffect, useState } from "react";
import { API_URL } from "../services/api";

const defaultWsUrl = API_URL.startsWith("https")
  ? API_URL.replace(/^https/, "wss") + "/ws/dashboard"
  : API_URL.replace(/^http/, "ws") + "/ws/dashboard";

const WS_URL = import.meta.env.VITE_WS_URL || defaultWsUrl;

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

