export interface Patient{
    id: string;
    patient_no: string;
    name: string;
    birth_date: string | null;
    estimated_age: number |null;
    sex: string |null;
    phone: string | null;
    status: string;

}

export interface PatientListResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: Patient[];
}