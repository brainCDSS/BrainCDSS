import {
  useState,
} from "react";

import AppShell from
  "../shared/layout/AppShell";

import Dashboard from
  "../features/dashboard/Dashboard";

import LoginPage from
  "../features/auth/LoginPage";

import {
  clearAuthSession,
  loadAuthSession,
} from "../features/auth/session";

import type {
  LoginResponse,
} from "../features/auth/types";


/**
 * Brain CDSS App
 *
 * 로그인 전:
 * LoginPage 표시
 *
 * 로그인 후:
 * 기존 AppShell과 Dashboard 표시
 */
export function App() {

  const [
    authSession,
    setAuthSession,
  ] = useState<LoginResponse | null>(
    () => loadAuthSession(),
  );

  function handleLogout() { //로그아웃 함수
    clearAuthSession();
    setAuthSession(null);
  }

  if (!authSession) {

    return (
      <LoginPage
        onLoginSuccess={
          setAuthSession
        }
      />
    );

  }


  return (
    <AppShell
      currentUser={authSession.user}
      onLogout={handleLogout}
    >
      {(onOpenPatient, onOpenMenu) => (
        <Dashboard
          currentUser={authSession.user}
          onOpenPatient={onOpenPatient}
          onOpenMenu={onOpenMenu}
        />
      )}
    </AppShell>
);

}


export default App;
