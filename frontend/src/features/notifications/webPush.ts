import {
  getToken,
  onMessage,
} from "firebase/messaging";

import {
  firebaseVapidKey,
  firebaseWebConfig,
  getFirebaseMessaging,
  isFirebaseConfigured,
} from "../../lib/firebase";

import {
  registerWebFcmToken,
} from "./api";


const DEVICE_ID_KEY =
  "brainon-web-device-id";

let foregroundListenerRegistered =
  false;


function getOrCreateDeviceId() {
  const existing =
    localStorage.getItem(
      DEVICE_ID_KEY,
    );

  if (existing) {
    return existing;
  }

  const deviceId =
    `web-${crypto.randomUUID()}`;

  localStorage.setItem(
    DEVICE_ID_KEY,
    deviceId,
  );

  return deviceId;
}


function createServiceWorkerUrl() {
  const params =
    new URLSearchParams({
      apiKey:
        String(
          firebaseWebConfig.apiKey ?? "",
        ),

      authDomain:
        String(
          firebaseWebConfig.authDomain ?? "",
        ),

      projectId:
        String(
          firebaseWebConfig.projectId ?? "",
        ),

      storageBucket:
        String(
          firebaseWebConfig.storageBucket ?? "",
        ),

      messagingSenderId:
        String(
          firebaseWebConfig.messagingSenderId ?? "",
        ),

      appId:
        String(
          firebaseWebConfig.appId ?? "",
        ),
    });

  return (
    `/firebase-messaging-sw.js?${params.toString()}`
  );
}


export async function connectWebPush() {
  if (!isFirebaseConfigured) {
    throw new Error(
      "FIREBASE_NOT_CONFIGURED",
    );
  }

  if (!("Notification" in window)) {
    throw new Error(
      "WEB_NOTIFICATION_NOT_SUPPORTED",
    );
  }

  if (!("serviceWorker" in navigator)) {
    throw new Error(
      "SERVICE_WORKER_NOT_SUPPORTED",
    );
  }

  const permission =
    await Notification.requestPermission();

  if (permission !== "granted") {
    throw new Error(
      `NOTIFICATION_PERMISSION_${permission.toUpperCase()}`,
    );
  }

  const registration =
    await navigator.serviceWorker.register(
      createServiceWorkerUrl(),
      {
        scope: "/",
      },
    );

  const messaging =
    await getFirebaseMessaging();

  const token =
    await getToken(
      messaging,
      {
        vapidKey:
          firebaseVapidKey,

        serviceWorkerRegistration:
          registration,
      },
    );

  if (!token) {
    throw new Error(
      "FCM_WEB_TOKEN_EMPTY",
    );
  }

  const apiResult =
    await registerWebFcmToken({
      device_id:
        getOrCreateDeviceId(),

      platform:
        "WEB",

      token,
    });

  if (!foregroundListenerRegistered) {
    foregroundListenerRegistered =
      true;

    onMessage(
      messaging,
      async (payload) => {
        await registration.showNotification(
          payload.notification?.title ??
            "BrainOn",

          {
            body:
              payload.notification?.body ??
              "",
            data:
              payload.data ?? {},
          },
        );
      },
    );
  }

  return {
    tokenLength:
      token.length,

    tokenId:
      apiResult.token_id,

    deviceId:
      apiResult.device_id,
  };
}
