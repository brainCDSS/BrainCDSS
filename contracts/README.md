# 서비스 계약

목적: producer와 consumer가 구현 전에 REST, event, MCP, CDS Hooks, DICOM output, model bundle 경계를 검토한다. 이곳에는 실제 환자 payload를 넣지 않는다. 주요 진입점은 하위 JSON Schema와 README이며 `python tests/contract/validate_contracts.py`로 검사한다. 변경 시 additive 변경을 우선하고 breaking change는 major schema/API version을 올려 병행 운영한다.
