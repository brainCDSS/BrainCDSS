import {
  GeminiProvider,
} from "./gemini/provider.js";

import type {
  AssistantProvider,
} from "./provider.js";


export type ProviderMode =
  | "vertex";


export type ProviderBundle = {
  provider: AssistantProvider;
  mode: ProviderMode;
  model: string;
};


function requiredEnv(
  name: string,
): string {
  const value =
    process.env[name]
      ?.trim()
    ?? "";

  if (!value) {
    throw new Error(
      `${name}_REQUIRED`
    );
  }

  return value;
}


export function createProvider():
  ProviderBundle {

  const project =
    requiredEnv(
      "GOOGLE_CLOUD_PROJECT"
    );

  const location =
    requiredEnv(
      "GOOGLE_CLOUD_LOCATION"
    );

  const model =
    requiredEnv(
      "GEMINI_MODEL"
    );

  return {
    provider:
      new GeminiProvider({
        project,
        location,
        model,
      }),

    mode: "vertex",

    model,
  };
}
