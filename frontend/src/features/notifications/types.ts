export type NotificationType =
  | "EMERGENCY"
  | "CONSULTATION"
  | "IMAGING"
  | "AI_ANALYSIS"
  | "APPOINTMENT"
  | "SYSTEM";

export interface NotificationData extends Record<string, unknown> {
  requester_name?: string;
  actor_name?: string;
  patient_name?: string;
  patient_id?: string;
  encounter_id?: string;
  emergency_event_id?: string;
  triage_priority?: "EMERGENCY" | "URGENT" | "NON_EMERGENCY";
  event_type?: string;
  related_url?: string;
  url?: string;
  path?: string;
}

export interface NotificationItem{id:string;category:NotificationType|string;severity:string;title:string;body:string;data:NotificationData;is_read:boolean;read_at:string|null;created_at:string}
export interface NotificationListResponse{count?:number|null;unread_count?:number|null;next?:string|null;previous?:string|null;results?:NotificationItem[]|null}
export interface NotificationPreferences { dnd:{enabled:boolean;start:string|null;end:string|null;timezone:string};categories:Array<{category:string;enabled:boolean;required:boolean}>;updated_at?:string }
