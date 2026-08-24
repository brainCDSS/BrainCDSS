# MCP rules
PostgreSQL에 직접 접근하지 않는다. 모든 tool은 Django API 조회만 하며 actor role, patient scope, trace/audit를 전달한다. 상태 변경 tool을 만들지 않는다.
