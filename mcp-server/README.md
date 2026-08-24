# MCP server

목적: Clinical Tool의 조회 전용 schema/handler와 Django 내부 API client 경계를 제공한다. DB 직접 접근·상태변경 tool·실제 환자 data는 금지한다. 공식 MCP SDK를 확인하지 못해 transport는 TODO이며 현재 registry와 MockBackendClient만 test 가능하다. `python -m pytest mcp-server/tests`; 환경변수는 backend URL/token. 다음 작업은 공식 SDK 검증과 Django internal endpoint 계약이다.
