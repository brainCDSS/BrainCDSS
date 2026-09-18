export const NOTIFICATION_STATE_CHANGED_EVENT =
  "brainon:notification-state-changed";


export function emitNotificationStateChanged() {
  window.dispatchEvent(
    new Event(
      NOTIFICATION_STATE_CHANGED_EVENT,
    ),
  );
}
