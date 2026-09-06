import AppShell from "../shared/layout/AppShell";
import Dashboard from "../features/dashboard/Dashboard";


/**
 * Brain CDSS App
 *
 * AppShell의 기본 children은 Dashboard이다.
 *
 * Sidebar 메뉴에 따라
 * AppShell 내부에서 Worklist / Triage 등의
 * 화면으로 전환한다.
 */
export function App() {
  return (
    <AppShell>
      <Dashboard />
    </AppShell>
  );
}


export default App;