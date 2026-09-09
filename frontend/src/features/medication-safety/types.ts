export interface MedicationItem{medication_id:string;medication_code:string;medication_name:string;dosage_form:string;strength:string;manufacturer:string;is_active:boolean}
export interface MedicationListResponse{count:number;results:MedicationItem[]}
