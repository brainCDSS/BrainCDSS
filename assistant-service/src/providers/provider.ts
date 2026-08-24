/** Provider boundary avoids guessing an unverified Genkit/Gemini SDK API. */
export interface AssistantProvider { generate(input: {role:'patient'|'clinician'; prompt:string}): Promise<{text:string;usageTokens:number}>; }
