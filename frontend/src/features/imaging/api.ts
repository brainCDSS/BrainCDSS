import { apiRequest } from "../../api/client";

import type {
  ImagingStudy,
} from "./types";


export async function getImagingStudies(): Promise<ImagingStudy[]> {
  return apiRequest<ImagingStudy[]>(
    "/api/v1/imaging/studies",
  );
}