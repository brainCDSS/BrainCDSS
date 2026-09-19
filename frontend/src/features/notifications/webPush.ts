import {
  getToken,
  onMessage,
} from "firebase/messaging";

import type {
  MessagePayload,
  Messaging,
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

import {
  emitNotificationStateChanged,
} from "./events";


const DEVICE_ID_KEY =
  "brainon-web-device-id";

let foregroundListenerRegistered =
  false;

let serviceWorkerListenerRegistered =
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
          firebaseWebConfig.apiKey ??
          "",
        ),

      authDomain:
        String(
          firebaseWebConfig.authDomain ??
          "",
        ),

      projectId:
        String(
          firebaseWebConfig.projectId ??
          "",
        ),

      storageBucket:
        String(
          firebaseWebConfig.storageBucket ??
          "",
        ),

      messagingSenderId:
        String(
          firebaseWebConfig.messagingSenderId ??
          "",
        ),

      appId:
        String(
          firebaseWebConfig.appId ??
          "",
        ),
    });

  return (
    `/firebase-messaging-sw.js?${params.toString()}`
  );
}


function installServiceWorkerBridge() {
  if (
    serviceWorkerListenerRegistered
  ) {
    return;
  }

  serviceWorkerListenerRegistered =
    true;

  navigator.serviceWorker.addEventListener(
    "message",
    (event) => {
      if (
        event.data?.type !==
        "BRAINON_FCM_BACKGROUND"
      ) {
        return;
      }

      console.info(
        "BRAINON_FCM_BACKGROUND_RECEIVED",
        event.data.payload,
      );

      emitNotificationStateChanged();
    },
  );
}


function installForegroundListener(
  messaging: Messaging,
  registration: ServiceWorkerRegistration,
) {
  if (foregroundListenerRegistered) {
    return;
  }

  foregroundListenerRegistered =
    true;

  onMessage(
    messaging,
    async (
      payload: MessagePayload,
    ) => {
      console.info(
        "BRAINON_FCM_FOREGROUND_RECEIVED",
        payload,
      );

      emitNotificationStateChanged();

      if (
        Notification.permission !==
        "granted"
      ) {
        return;
      }

      const title =
        payload.notification?.title ??
        payload.data?.title ??
        "BrainOn";

      const body =
        payload.notification?.body ??
        payload.data?.body ??
        "";

      const notificationId =
        payload.data?.notification_id ??
        crypto.randomUUID();

      try {
        await registration.showNotification(
          title,
          {
            body,
            data:
              payload.data ?? {},
            tag:
              `brainon-${notificationId}`,
          },
        );

        console.info(
          "BRAINON_FOREGROUND_NOTIFICATION_SHOWN",
          notificationId,
        );
      } catch (error) {
        console.error(
          "BRAINON_FOREGROUND_NOTIFICATION_FAILED",
          error,
        );
      }
    },
  );
}


export async function connectWebPush() {
  if (!isFirebaseConfigured) {
    throw new Error(
      "FIREBASE_NOT_CONFIGURED",
    );
  }

  if (
    !("Notification" in window)
  ) {
    throw new Error(
      "WEB_NOTIFICATION_NOT_SUPPORTED",
    );
  }

  if (
    !("serviceWorker" in navigator)
  ) {
    throw new Error(
      "SERVICE_WORKER_NOT_SUPPORTED",
    );
  }

  const permission =
    await Notification.requestPermission();

  if (
    permission !== "granted"
  ) {
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

  try {
    await registration.update();
  } catch (error) {
    console.warn(
      "BRAINON_SERVICE_WORKER_UPDATE_FAILED",
      error,
    );
  }

  const messaging =
    await getFirebaseMessaging();

  installServiceWorkerBridge();

  installForegroundListener(
    messaging,
    registration,
  );

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

  console.info(
    "BRAINON_WEB_PUSH_READY",
    {
      deviceId:
        apiResult.device_id,
      tokenLength:
        token.length,
    },
  );

  return {
    tokenLength:
      token.length,

    tokenId:
      apiResult.token_id,

    deviceId:
      apiResult.device_id,
  };
}
