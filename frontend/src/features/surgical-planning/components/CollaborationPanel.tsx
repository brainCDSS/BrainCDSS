import { useState } from "react";
import type { CollaborationMessage, ViewAttachment, ViewerMode } from "../types";

interface Props { messages: CollaborationMessage[]; viewerMode: ViewerMode; selectedClipInstanceId: string | null; placedClipCount: number; sending: boolean; enabled: boolean; onSend: (message: string, attachment?: ViewAttachment) => Promise<void> }
export default function CollaborationPanel({ messages, viewerMode, selectedClipInstanceId, placedClipCount, sending, enabled, onSend }: Props) {
  const [draft, setDraft] = useState(""); const [shareView, setShareView] = useState(false);
  const submit = async () => { const message = draft.trim(); if (!message) return; const attachment = shareView ? { viewerMode, selectedClipInstanceId, placedClipCount } : undefined; await onSend(message, attachment); setDraft(""); setShareView(false); };
  return <div className="collaboration-panel">
    <div className="collaboration-panel__notice"><strong>협업 메시지</strong><span>REST 저장·조회 연결 · 실시간 WebSocket은 미지원</span></div>
    <div className="collaboration-messages" aria-live="polite">{messages.length ? messages.map((item) => <article className="collaboration-message" key={item.id}><header><strong>{item.sender.name}</strong><span>{item.sender.role}</span></header><p>{item.message}</p>{item.attachment && <div className="collaboration-attachment"><strong>Viewer 상태 공유</strong><span>{item.attachment.viewerMode} · 클립 {item.attachment.placedClipCount}개</span></div>}<time dateTime={item.createdAt}>{new Date(item.createdAt).toLocaleTimeString("ko-KR", { hour: "2-digit", minute: "2-digit" })}</time></article>) : <p className="planning-compact-state">아직 공유된 메시지가 없습니다.</p>}</div>
    <div className="collaboration-composer"><label><span>메시지</span><textarea value={draft} disabled={!enabled || sending} onChange={(event) => setDraft(event.target.value)} placeholder={enabled ? "협업 메시지를 입력하세요." : "플래닝을 먼저 저장하세요."}/></label><label className="collaboration-share-toggle"><input type="checkbox" checked={shareView} disabled={!enabled || sending} onChange={(event) => setShareView(event.target.checked)}/>현재 Viewer / Clip 상태 첨부</label><button className="clinical-action clinical-action--primary" onClick={() => void submit()} disabled={!enabled || sending || !draft.trim()} type="button">{sending ? "전송 중..." : "메시지 전송"}</button></div>
  </div>;
}
