/** Minimal shell; clinical screens remain explicit placeholders. */
//export function App() { return <main><header><h1>BrainOn CDSS</h1><p>의료진 웹 개발 골격</p></header><section aria-labelledby="health"><h2 id="health">Health</h2><p data-testid="status">Frontend shell is ready.</p></section></main>; }


import AppShell from "../shared/layout/AppShell";
import Dashboard from "../features/dashboard/Dashboard";

export function App() {
  return (
    <AppShell>
      <Dashboard />
    </AppShell>
  );
}

export default App;