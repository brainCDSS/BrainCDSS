# Inference

목적: 학습이 아닌 배포용 의료영상 추론 API·orchestrator·MOSEC worker adapter·model loader·전후처리·DICOM SEG/SR 경계를 제공한다. 모델 가중치, dataset, training/experiment는 금지한다. 진입점은 `src.api.main:app`; `python -m uvicorn src.api.main:app --port 8100`(inference에서 실행). 테스트는 `python -m pytest inference/tests`. `MODEL_BUNDLE_URI`, GCS/MLflow 설정을 사용한다. 미설정 상태는 `MODEL_NOT_CONFIGURED`; 다음 작업은 승인된 bundle handoff 후 adapter 구현이다.
