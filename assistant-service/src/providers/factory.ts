import { GeminiProvider } from "./gemini/provider.js";
import { MockProvider } from "./mock.js";

import type {
  AssistantProvider,
} from "./provider.js";


export type ProviderMode =
  | "mock"
  | "gemini";


export type ProviderBundle = {
  provider: AssistantProvider;
  mode: ProviderMode;
  model: string | null;
};


export function createProvider():
  ProviderBundle {

  const apiKey =
    process.env.GEMINI_API_KEY
      ?.trim()
    ?? "";

  if (!apiKey) {
    return {
      provider: new MockProvider(),
      mode: "mock",
      model: null,
    };
  }

  const model =
    process.env.GEMINI_MODEL
      ?.trim()
    ?? "";

  if (
    !model
    || model.startsWith("TODO")
  ) {
    throw new Error(
      "GEMINI_API_KEY is configured "
      + "but GEMINI_MODEL is missing."
    );
  }

  return {
    provider: new GeminiProvider(
      apiKey,
      model,
    ),
    mode: "gemini",
    model,
  };
}
