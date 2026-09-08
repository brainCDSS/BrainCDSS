export interface NotificationItem{id:string;category:string;severity:string;title:string;body:string;data:Record<string,unknown>;is_read:boolean;read_at:string|null;created_at:string}
export interface NotificationListResponse{count:number;unread_count:number;next?:string|null;previous?:string|null;results:NotificationItem[]}
