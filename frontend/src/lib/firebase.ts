import {
  getApps,
  initializeApp,
  type FirebaseOptions,
} from "firebase/app";

import {
  getMessaging,
  isSupported,
  type Messaging,
} from "firebase/messaging";


function requiredEnv(
  name: string,
  value: string | undefined,
): string {
  if (!value) {
    throw new Error(
      `FIREBASE_ENV_MISSING:${name}`,
    );
  }

  return value;
}


export const firebaseWebConfig: FirebaseOptions = {
  apiKey: requiredEnv(
    "VITE_FIREBASE_API_KEY",
    import.meta.env.VITE_FIREBASE_API_KEY,
  ),

  authDomain: requiredEnv(
    "VITE_FIREBASE_AUTH_DOMAIN",
    import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
  ),

  projectId: requiredEnv(
    "VITE_FIREBASE_PROJECT_ID",
    import.meta.env.VITE_FIREBASE_PROJECT_ID,
  ),

  storageBucket: requiredEnv(
    "VITE_FIREBASE_STORAGE_BUCKET",
    import.meta.env.VITE_FIREBASE_STORAGE_BUCKET,
  ),

  messagingSenderId: requiredEnv(
    "VITE_FIREBASE_MESSAGING_SENDER_ID",
    import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID,
  ),

  appId: requiredEnv(
    "VITE_FIREBASE_APP_ID",
    import.meta.env.VITE_FIREBASE_APP_ID,
  ),
};


export const firebaseVapidKey =
  requiredEnv(
    "VITE_FIREBASE_VAPID_KEY",
    import.meta.env.VITE_FIREBASE_VAPID_KEY,
  );


const firebaseApp =
  getApps()[0] ??
  initializeApp(
    firebaseWebConfig,
  );


export async function getFirebaseMessaging():
Promise<Messaging> {

  if (!(await isSupported())) {
    throw new Error(
      "WEB_FCM_NOT_SUPPORTED",
    );
  }

  return getMessaging(
    firebaseApp,
  );
}
