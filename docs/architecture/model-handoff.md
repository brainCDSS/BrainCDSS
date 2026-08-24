# Model handoff
별도 brainon-model-training이 GCS bundle과 MLflow metadata를 발행한다. 이 저장소는 manifest/checksum과 deployment adapter만 관리하며 dataset, weight, training code를 받지 않는다.

