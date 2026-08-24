# Repository layout
Runtime 서비스와 contracts, tools, mocks, infra, cross-service tests, docs를 분리한다. 모바일은 독립 배포되는 환자·의료진 앱과 작은 shared package 영역으로 구성한다. Django는 업무 modular monolith이며 새 서비스는 ADR 없이 추가하지 않는다.
