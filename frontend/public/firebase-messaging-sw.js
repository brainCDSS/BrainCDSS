/* eslint-disable no-undef */

importScripts(
  "https://www.gstatic.com/firebasejs/12.19.0/firebase-app-compat.js",
);

importScripts(
  "https://www.gstatic.com/firebasejs/12.19.0/firebase-messaging-compat.js",
);

const params =
  new URL(
    self.location.href,
  ).searchParams;

firebase.initializeApp({
  apiKey:
    params.get("apiKey"),

  authDomain:
    params.get("authDomain"),

  projectId:
    params.get("projectId"),

  storageBucket:
    params.get("storageBucket"),

  messagingSenderId:
    params.get("messagingSenderId"),

  appId:
    params.get("appId"),
});

firebase.messaging();
