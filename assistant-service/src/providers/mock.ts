import type {
  AssistantProvider,
  AssistantRole,
} from "./provider.js";


export class MockProvider
  implements AssistantProvider {

  async generate(input: {
    role: AssistantRole;
    prompt: string;
  }) {
    return {
      text: (
        `MOCK:${input.role}:`
        + "요청이 접수되었습니다. "
        + "의료진 판단을 대체하지 않습니다."
      ),
      usageTokens: 0,
    };
  }
}
