import {apiRequest} from "../../api/client";
import type {NotificationItem,NotificationListResponse,NotificationPreferences} from "./types";
export function getNotifications(filters:{unreadOnly?:boolean;category?:string}={}){const p=new URLSearchParams();if(filters.unreadOnly)p.set("unread_only","true");if(filters.category)p.set("category",filters.category);const q=p.toString();return apiRequest<NotificationListResponse>(`/api/v1/notifications${q?`?${q}`:""}`)}
export function markNotificationRead(id:string){return apiRequest<Partial<NotificationItem>&Pick<NotificationItem,"id"|"is_read">>(`/api/v1/notifications/${encodeURIComponent(id)}/read`,{method:"PATCH"})}
export function getNotificationPreferences(){return apiRequest<NotificationPreferences>("/api/v1/notification-preferences")}
export function updateNotificationPreferences(payload:{dnd_enabled:boolean;dnd_start?:string|null;dnd_end?:string|null;categories?:Record<string,boolean>}){return apiRequest<NotificationPreferences>("/api/v1/notification-preferences",{method:"PATCH",headers:{"Content-Type":"application/json"},body:JSON.stringify(payload)})}

export interface FcmTokenRegistrationResponse {
  token_id: string;
  device_id: string;
  platform: "WEB";
  is_active: boolean;
  last_seen_at: string;
}

export function registerWebFcmToken(
  payload: {
    device_id: string;
    platform: "WEB";
    token: string;
  },
) {
  return apiRequest<FcmTokenRegistrationResponse>(
    "/api/v1/devices/fcm-tokens",
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    },
  );
}
