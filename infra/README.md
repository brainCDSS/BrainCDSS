# Infrastructure

목적: local Compose 설정과 RabbitMQ, Orthanc/OHIF, MLflow, observability, GCP 빈 template을 관리한다. secret·실제 의료데이터·cloud deployment 결과는 두지 않는다. 진입점은 root compose; `docker compose config` 및 profile별 `up`. 환경변수는 root example. 다음 작업은 조직별 provisioning 승인이다.
