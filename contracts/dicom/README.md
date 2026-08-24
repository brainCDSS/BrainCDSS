# DICOM SEG/SR responsibility

Inference가 pixel/measurement 결과를 DICOM SEG/SR 후보로 직렬화하고 참조 instance·algorithm/model version을 기록한다. Backend는 workflow 상태와 의료진 검토를 관리한다. 실제 생성·검증은 TODO이며 미검증 결과를 임상 확정으로 표시하지 않는다.
