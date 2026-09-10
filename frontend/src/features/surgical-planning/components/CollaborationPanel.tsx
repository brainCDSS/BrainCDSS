import { useState } from "react";
import type { CollaborationMessage, CollaborationUser, ViewAttachment, ViewerMode } from "../types";

interface Props { currentUser: CollaborationUser; messages: CollaborationMessage[]; viewerMode: ViewerMode; selectedClipInstanceId: string | null; placedClipCount: number; onSend: (message: CollaborationMessage) => void }
export default function CollaborationPanel({ currentUser, messages, viewerMode, selectedClipInstanceId, placedClipCount, onSend }: Props) {
  const [draft, setDraft] = useState(""); const [shareView, setShareView] = useState(false);
  const submit = () => { const message = draft.trim(); if (!message) return; const attachment: ViewAttachment | undefined = shareView ? { viewerMode, selectedClipInstanceId, placedClipCount } : undefined; onSend({ id: globalThis.crypto?.randomUUID?.() ?? `local-message-${Date.now()}`, sender: currentUser, message, createdAt: new Date().toISOString(), attachment }); setDraft(""); setShareView(false); };
  return <div className="collaboration-panel">
    <div className="collaboration-panel__notice"><strong>로컬 협업 미리보기</strong><span>WebSocket API 미연동 · 메시지는 새로고침 시 유지되지 않습니다.</span></div>
    <div className="collaboration-messages" aria-live="polite">{messages.length ? messages.map((item) => <article className="collaboration-message" key={item.id}><header><strong>{item.sender.name}</strong><span>{item.sender.role}</span></header><p>{item.message}</p>{item.attachment && <div className="collaboration-attachment"><strong>Viewer 상태 공유</strong><span>{item.attachment.viewerMode} · 클립 {item.attachment.placedClipCount}개</span></div>}<time dateTime={item.createdAt}>{new Date(item.createdAt).toLocaleTimeString("ko-KR", { hour: "2-digit", minute: "2-digit" })}</time></article>) : <p className="planning-compact-state">아직 공유된 메시지가 없습니다.</p>}</div>
    <div className="collaboration-composer"><label><span>메시지</span><textarea value={draft} onChange={(event) => setDraft(event.target.value)} placeholder="협업 메시지를 입력하세요."/></label><label className="collaboration-share-toggle"><input type="checkbox" checked={shareView} onChange={(event) => setShareView(event.target.checked)}/>현재 Viewer / Clip 상태 첨부</label><button className="clinical-action clinical-action--primary" onClick={submit} disabled={!draft.trim()} type="button">메시지 전송</button></div>
  </div>;
}
