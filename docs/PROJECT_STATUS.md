# Project status

| 상태 | 항목 |
|---|---|
| Backend 구현 완료 | JWT/RBAC, request_id·trace_id, Audit 기반, DUR DDI/DOSE 저장·활성화, Medication Safety, RX-004, CDS Hooks 4종 |
| 비동기 처리 확인 완료 | RabbitMQ broker, Celery Worker, DUR Sync Celery Task, Outbox publish task 등록 |
| API 검증 완료 | Django check, 핵심 E2E, Swagger/OpenAPI Schema, CDS Service JWT 및 Discovery 실제 HTTP 호출 |
| DUR 실제 연동 확인 | MFDS DUR OpenAPI DDI(병용금기)·DOSE(용량주의) 수집 및 PostgreSQL 저장 |
| 추가 데이터 확장 필요 | DUPLICATE, AGE, ELDERLY, PREGNANCY 등 추가 약물안전성 기준정보 |
| 계속 구현 중 | Imaging/Orthanc 연동, 실제 AI inference 연계, 일부 임상 workflow 및 Frontend 통합 |
| 외부 계정·Secret 필요 | GCP/GCS, DUR 운영 Key, Service JWT 운영 Key, Gemini/FCM 등 배포 환경 Secret |
| 최종 통합 단계 수행 예정 | 전체 Backend Test, Swagger/Postman 회귀 검증, Frontend-Backend 통합테스트, 배포 검증 |

> 실제 환자정보, 운영 Secret, API Key 또는 비식별화되지 않은 의료영상은 저장소에 commit하지 않는다.
