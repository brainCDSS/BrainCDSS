import {
  useState,
} from "react";

import AppShell from
  "../shared/layout/AppShell";

import Dashboard from
  "../features/dashboard/Dashboard";

import NurseDashboard from
  "../features/dashboard/NurseDashboard";

import LoginPage from
  "../features/auth/LoginPage";

import {
  clearAuthSession,
  loadAuthSession,
} from "../features/auth/session";

import type {
  LoginResponse,
} from "../features/auth/types";


export function App() {
  const [
    authSession,
    setAuthSession,
  ] =
    useState<LoginResponse | null>(
      () =>
        loadAuthSession(),
    );


  function handleLogout() {
    clearAuthSession();

    setAuthSession(
      null,
    );
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


  const isNurse =
    authSession.user.role.code ===
    "NURSE";


  return (
    <AppShell
      currentUser={
        authSession.user
      }
      onLogout={
        handleLogout
      }
    >
      {(
        onOpenPatient,
        onOpenMenu,
      ) =>
        isNurse ? (
          <NurseDashboard
            currentUser={
              authSession.user
            }
            onOpenPatient={
              onOpenPatient
            }
            onOpenMenu={
              onOpenMenu
            }
          />
        ) : (
          <Dashboard
            currentUser={
              authSession.user
            }
            onOpenPatient={
              onOpenPatient
            }
            onOpenMenu={
              onOpenMenu
            }
          />
        )
      }
    </AppShell>
  );
}


export default App;