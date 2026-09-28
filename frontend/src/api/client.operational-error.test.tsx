// @vitest-environment jsdom

import {
  act,
} from "react";

import {
  createRoot,
} from "react-dom/client";

import {
  afterEach,
  describe,
  expect,
  it,
  vi,
} from "vitest";

import {
  ApiRequestError,
  apiRequest,
} from "./client";

import OperationalErrorHost from
  "../shared/errors/OperationalErrorHost";

import {
  OPERATIONAL_ERROR_EVENT,
  trackingCodeFromRequestId,
  type OperationalErrorPayload,
} from "../shared/errors/operationalError";


afterEach(() => {
  vi.unstubAllGlobals();

  document.body.innerHTML =
    "";
});


describe(
  "BrainOn operational error tracking",
  () => {

    it(
      "converts request UUID to ERR code",
      () => {

        const trackingCode =
          trackingCodeFromRequestId(
            "07949247-b315-4abc-9123-abcdef123456",
          );

        expect(
          trackingCode,
        ).toBe(
          "ERR-07949247B3154ABC",
        );
      },
    );


    it(
      "propagates request ID and ERR code on HTTP 500",
      async () => {

        const requestId =
          "07949247-b315-4abc-9123-abcdef123456";


        let received:
          OperationalErrorPayload
          | null = null;


        const listener = (
          event: Event,
        ) => {

          const customEvent = event as CustomEvent<OperationalErrorPayload>;

          received = customEvent.detail;
        };


        window.addEventListener(
          OPERATIONAL_ERROR_EVENT,
          listener,
        );


        vi.stubGlobal(
          "fetch",
          vi.fn(
            async () => {

              return new Response(
                JSON.stringify({
                  detail:
                    "internal failure",
                }),
                {
                  status:
                    500,

                  headers: {
                    "Content-Type":
                      "application/json",

                    "X-Request-ID":
                      requestId,
                  },
                },
              );
            },
          ),
        );


        let thrown:
          unknown = null;


        try {

          await apiRequest(
            "/api/v1/test-operational-error",
          );

        } catch (error) {

          thrown =
            error;
        }


        window.removeEventListener(
          OPERATIONAL_ERROR_EVENT,
          listener,
        );


        expect(
          thrown,
        ).toBeInstanceOf(
          ApiRequestError,
        );


        const apiError =
          thrown as ApiRequestError;


        expect(
          apiError.requestId,
        ).toBe(
          requestId,
        );


        expect(
          apiError.trackingCode,
        ).toBe(
          "ERR-07949247B3154ABC",
        );


        expect(
          received,
        ).toEqual({
          kind:
            "server",

          status:
            500,

          requestId,

          trackingCode:
            "ERR-07949247B3154ABC",
        });
      },
    );


    it(
      "prefers Backend X-Tracking-Code",
      async () => {

        const requestId =
          "07949247-b315-4abc-9123-abcdef123456";

        const backendTrackingCode =
          "ERR-AAAAAAAAAAAAAAAA";


        vi.stubGlobal(
          "fetch",
          vi.fn(
            async () => {

              return new Response(
                JSON.stringify({
                  detail:
                    "backend failure",
                }),
                {
                  status:
                    503,

                  headers: {
                    "Content-Type":
                      "application/json",

                    "X-Request-ID":
                      requestId,

                    "X-Tracking-Code":
                      backendTrackingCode,
                  },
                },
              );
            },
          ),
        );


        let thrown:
          unknown = null;


        try {

          await apiRequest(
            "/api/v1/test-backend-code",
          );

        } catch (error) {

          thrown =
            error;
        }


        const apiError =
          thrown as ApiRequestError;


        expect(
          apiError.trackingCode,
        ).toBe(
          backendTrackingCode,
        );
      },
    );


    it(
      "renders the center popup with the same ERR code",
      async () => {

        const container =
          document.createElement(
            "div",
          );


        document.body.appendChild(
          container,
        );


        const root =
          createRoot(
            container,
          );


        await act(
          async () => {

            root.render(
              <OperationalErrorHost />,
            );
          },
        );


        const payload:
          OperationalErrorPayload = {

          kind:
            "server",

          status:
            500,

          requestId:
            "07949247-b315-4abc-9123-abcdef123456",

          trackingCode:
            "ERR-07949247B3154ABC",
        };


        await act(
          async () => {

            window.dispatchEvent(
              new CustomEvent(
                OPERATIONAL_ERROR_EVENT,
                {
                  detail:
                    payload,
                },
              ),
            );
          },
        );


        expect(
          container.textContent,
        ).toContain(
          "요청을 처리할 수 없습니다",
        );


        expect(
          container.textContent,
        ).toContain(
          "관리자에게 문의해 주세요",
        );


        expect(
          container.textContent,
        ).toContain(
          "ERR-07949247B3154ABC",
        );


        await act(
          async () => {

            root.unmount();
          },
        );
      },
    );
  },
);
