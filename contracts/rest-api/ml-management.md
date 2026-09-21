# ML 관리 API 계약

모든 엔드포인트는 인증된 `SYSTEM_ADMIN` 역할만 사용할 수 있다. 모델 가중치,
환자 정보, 원본 영상은 반환하거나 변경하지 않는다.

## 운영 현황 조회

`GET /api/v1/admin/ml/overview`

응답은 `models`, `versions`, `routing_configs` 배열을 포함한다. 버전에는 MLflow
메타데이터, 검증 상태(`DRAFT|VALIDATED|APPROVED|RETIRED`), 운영 가능 여부와 성능
지표가 포함된다. 라우팅에는 modality, analysis type, 대상 모델 버전, 활성 여부가
포함된다.

## 버전 사용 승인

`POST /api/v1/admin/ml/model-versions/{version_id}/approve`

본문은 `{ "reason": string, "confirmation": true }`이다. `VALIDATED` 상태이며
활성 모델 설정이 존재하는 버전만 `APPROVED`로 전환할 수 있다. 승인만으로 운영
라우팅은 바뀌지 않는다.

## 버전 사용 종료

`POST /api/v1/admin/ml/model-versions/{version_id}/retire`

본문은 승인과 동일하다. 활성 모델 또는 활성 라우팅이 참조하는 버전은 종료할 수
없다. 기존 분석의 버전 스냅샷은 변경하지 않는다.

## 라우팅 생성 및 운영 전환

`POST /api/v1/admin/ml/routing-configs`는 비활성 라우팅을 생성한다. 본문은
`version`, `modality`, `analysis_type`, `target_model_version_id`, `reason`을 포함한다.
대상은 승인된 모델 버전이고 해당 modality를 지원해야 한다.

`POST /api/v1/admin/ml/routing-configs/{routing_id}/activate`의 본문은
`{ "reason": string, "confirmation": true }`이다. 같은 modality와 analysis type의
기존 활성 라우팅은 비활성화되고, 선택한 라우팅이 활성화된다. 과거 비활성 라우팅을
다시 활성화하는 방식이 롤백이다.
