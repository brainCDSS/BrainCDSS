# test_results

목적: test_results domain 책임을 캡슐화한다. 승인된 model, service, selector, API, task만 이곳에 둔다. 다른 domain의 내부 구현, 실제 의료데이터, 추측한 임상 규칙은 두지 않는다. 진입점은 apps.py이며 전체 Django 명령으로 실행·test한다. 환경변수는 root example을 따른다. 다음 작업은 domain/API 명세 확정이다.

