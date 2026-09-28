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


export const firebaseWebConfig: FirebaseOptions = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY ?? "",
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN ?? "",
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID ?? "",
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET ?? "",
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID ?? "",
  appId: import.meta.env.VITE_FIREBASE_APP_ID ?? "",
};


export const firebaseVapidKey = import.meta.env.VITE_FIREBASE_VAPID_KEY ?? "";

export const isFirebaseConfigured = [
  firebaseWebConfig.apiKey,
  firebaseWebConfig.authDomain,
  firebaseWebConfig.projectId,
  firebaseWebConfig.storageBucket,
  firebaseWebConfig.messagingSenderId,
  firebaseWebConfig.appId,
  firebaseVapidKey,
].every((value) => typeof value === "string" && value.trim().length > 0);


export async function getFirebaseMessaging():
Promise<Messaging> {

  if (!isFirebaseConfigured) {
    throw new Error(
      "FIREBASE_NOT_CONFIGURED",
    );
  }

  if (!(await isSupported())) {
    throw new Error(
      "WEB_FCM_NOT_SUPPORTED",
    );
  }

  const firebaseApp =
    getApps()[0] ??
    initializeApp(
      firebaseWebConfig,
    );

  return getMessaging(firebaseApp);
}
