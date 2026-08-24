# 보안 및 의료데이터 정책

- 실제 환자정보, 의료영상, 비식별화되지 않은 DICOM/NIfTI를 저장하지 않는다.
- `.env`, Gemini/FCM key, GCP service-account key를 commit하지 않는다.
- 로그·trace·audit payload에 환자 식별정보나 원문 임상기록을 남기지 않는다.
- RBAC와 audit log를 우회하지 않는다.
- MCP server는 DB에 직접 접근하지 않고 승인된 Django 내부 API만 조회한다.
- AI 결과는 의료진의 최종 판단을 보조할 뿐 진단·처방 확정·기록 변경을 자동 수행하지 않는다.

취약점은 공개 issue 대신 지정 채널로 보고한다. 보고 주소와 SLA: **TODO: 보안 담당 채널 확정**.
