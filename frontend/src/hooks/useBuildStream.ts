import { useEffect, useState, useRef } from "react";

export type BuildStreamStatus = "idle" | "streaming" | "done" | "error";

interface UseBuildStreamResult {
  lines: string[];
  status: BuildStreamStatus;
  start: (url: string) => void;
  reset: () => void;
}

export function useBuildStream(): UseBuildStreamResult {
  const [lines, setLines] = useState<string[]>([]);
  const [status, setStatus] = useState<BuildStreamStatus>("idle");
  const esRef = useRef<EventSource | null>(null);

  const start = (url: string) => {
    setLines([]);
    setStatus("streaming");
    const es = new EventSource(url);
    esRef.current = es;

    es.onmessage = (evt: MessageEvent) => {
      setLines((prev) => [...prev, evt.data as string]);
    };

    es.addEventListener("done", () => {
      setStatus("done");
      es.close();
    });

    es.onerror = () => {
      setStatus("error");
      es.close();
    };
  };

  const reset = () => {
    esRef.current?.close();
    setLines([]);
    setStatus("idle");
  };

  useEffect(() => {
    return () => {
      esRef.current?.close();
    };
  }, []);

  return { lines, status, start, reset };
}
