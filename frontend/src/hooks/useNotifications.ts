import { useEffect, useRef, useCallback } from "react";

export function useNotifications(onInterested: (sender: string) => void) {
  const permissionRef = useRef<NotificationPermission>("default");

  const requestPermission = useCallback(async () => {
    if (!("Notification" in window)) return;
    permissionRef.current = await Notification.requestPermission();
  }, []);

  const notify = useCallback(
    (sender: string) => {
      if (permissionRef.current === "granted") {
        new Notification("New interested reply", { body: sender });
      }
      onInterested(sender);
    },
    [onInterested],
  );

  useEffect(() => {
    void requestPermission();
  }, [requestPermission]);

  return { notify, requestPermission };
}
