import { Routes, Route } from 'react-router-dom';

function Home() {
  return (
    <div className="flex min-h-screen items-center justify-center">
      <p className="text-lg text-muted-foreground">Start prompting.</p>
    </div>
  );
}

export default function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
    </Routes>
  );
}
