import {apiRequest} from "../../api/client";import type{NotificationItem,NotificationListResponse,NotificationPreferences}from "./types";
export function getNotifications(unread=false){return apiRequest<NotificationListResponse>(`/api/v1/notifications${unread?"?unread_only=true":""}`)}
export function markNotificationRead(id:string){return apiRequest<NotificationItem>(`/api/v1/notifications/${encodeURIComponent(id)}/read`,{method:"PATCH"})}
export function getNotificationPreferences(){return apiRequest<NotificationPreferences>("/api/v1/notification-preferences")}
export function updateNotificationPreferences(payload:{dnd_enabled:boolean;dnd_start?:string|null;dnd_end?:string|null;categories?:Record<string,boolean>}){return apiRequest<NotificationPreferences>("/api/v1/notification-preferences",{method:"PATCH",headers:{"Content-Type":"application/json"},body:JSON.stringify(payload)})}
