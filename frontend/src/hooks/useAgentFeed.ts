import { useEffect, useRef, useState, useCallback } from "react";
import ApiClient from "@/services/ApiClient";
import type { AgentEvent } from "@/types/api";

export type AgentFeedStatus = "connected" | "reconnecting" | "lost" | "idle";

const MAX_EVENTS = 50;
const MAX_RECONNECTS = 10;

function getBackoffDelay(attempt: number): number {
  return Math.min(1000 * Math.pow(2, attempt), 30_000);
}

interface UseAgentFeedResult {
  events: AgentEvent[];
  status: AgentFeedStatus;
  connect: () => void;
  disconnect: () => void;
}

export function useAgentFeed(): UseAgentFeedResult {
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [status, setStatus] = useState<AgentFeedStatus>("idle");
  const reconnectCount = useRef(0);
  const cleanupRef = useRef<(() => void) | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const stopped = useRef(false);

  const connect = useCallback(() => {
    stopped.current = false;
    reconnectCount.current = 0;
    doConnect();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function doConnect() {
    if (stopped.current) return;

    setStatus("connected");

    const cleanup = ApiClient.subscribeAgentFeed((event: AgentEvent) => {
      setEvents((prev) => {
        const next = [event, ...prev];
        return next.slice(0, MAX_EVENTS);
      });
    });

    // Wrap cleanup with reconnection logic
    cleanupRef.current = () => {
      cleanup();
      if (!stopped.current) {
        if (reconnectCount.current >= MAX_RECONNECTS) {
          setStatus("lost");
          return;
        }
        setStatus("reconnecting");
        const delay = getBackoffDelay(reconnectCount.current);
        reconnectCount.current += 1;
        reconnectTimer.current = setTimeout(() => doConnect(), delay);
      }
    };
  }

  const disconnect = useCallback(() => {
    stopped.current = true;
    if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
    cleanupRef.current?.();
    setStatus("idle");
  }, []);

  useEffect(() => {
    return () => {
      stopped.current = true;
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
    };
  }, []);

  return { events, status, connect, disconnect };
}
