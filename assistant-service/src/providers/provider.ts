export type AssistantRole =
  | "patient"
  | "clinician";


export interface AssistantProvider {
  generate(input: {
    role: AssistantRole;
    prompt: string;
  }): Promise<{
    text: string;
    usageTokens: number;
  }>;
}
