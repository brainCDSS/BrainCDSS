/* eslint-disable no-undef */

/*
 * notificationclick listener는 Firebase SDK보다 먼저 등록한다.
 * Firebase Messaging이 생성한 notification의 data에는
 * FCM_MSG가 포함될 수 있으므로 두 구조를 모두 처리한다.
 */
self.addEventListener(
  "notificationclick",
  (event) => {
    event.notification.close();

    const raw =
      event.notification.data ?? {};

    const fcmMessage =
      raw.FCM_MSG ?? {};

    const customData =
      fcmMessage.data ??
      raw.data ??
      raw;

    const requestedTarget =
      customData.related_url ??
      customData.url ??
      customData.path ??
      "/";

    let targetUrl;

    try {
      targetUrl =
        new URL(
          requestedTarget,
          self.location.origin,
        ).href;
    } catch {
      targetUrl =
        new URL(
          "/",
          self.location.origin,
        ).href;
    }

    event.waitUntil(
      self.clients
        .matchAll({
          type: "window",
          includeUncontrolled: true,
        })
        .then(
          async (windowClients) => {
            for (
              const client
              of windowClients
            ) {
              if (
                "navigate" in client &&
                client.url !== targetUrl
              ) {
                try {
                  await client.navigate(
                    targetUrl,
                  );
                } catch {
                  // 기존 창 focus라도 유지한다.
                }
              }

              if (
                "focus" in client
              ) {
                return client.focus();
              }
            }

            if (
              self.clients.openWindow
            ) {
              return self.clients.openWindow(
                targetUrl,
              );
            }

            return undefined;
          },
        ),
    );
  },
);


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
    params.get(
      "messagingSenderId",
    ),

  appId:
    params.get("appId"),
});


const messaging =
  firebase.messaging();


messaging.onBackgroundMessage(
  (payload) => {
    /*
     * notification payload의 시스템 표시 자체는
     * Firebase Messaging이 담당한다.
     *
     * 여기서는 열린 BrainOn window들에게
     * 알림 상태 갱신 이벤트만 전달한다.
     * showNotification을 다시 호출하지 않아서
     * background Push 중복 표시를 방지한다.
     */
    self.clients
      .matchAll({
        type: "window",
        includeUncontrolled: true,
      })
      .then(
        (windowClients) => {
          for (
            const client
            of windowClients
          ) {
            client.postMessage({
              type:
                "BRAINON_FCM_BACKGROUND",

              payload: {
                notification:
                  payload.notification ??
                  null,

                data:
                  payload.data ??
                  {},
              },
            });
          }
        },
      );
  },
);
