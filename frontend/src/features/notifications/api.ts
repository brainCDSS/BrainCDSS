import {apiRequest} from "../../api/client";import type{NotificationItem,NotificationListResponse}from "./types";
export function getNotifications(unread=false){return apiRequest<NotificationListResponse>(`/api/v1/notifications${unread?"?unread_only=true":""}`)}
export function markNotificationRead(id:string){return apiRequest<NotificationItem>(`/api/v1/notifications/${encodeURIComponent(id)}/read`,{method:"PATCH"})}
