import { Link } from "react-router-dom";
import { Logo } from "../components/ui";

export default function NotFound() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 px-4 text-center">
      <Logo />
      <h1 className="h-page">Page not found</h1>
      <p className="text-ink-3">That page doesn't exist.</p>
      <div className="flex gap-2">
        <Link to="/" className="btn-secondary">Home</Link>
        <Link to="/app" className="btn-primary">Open the demo</Link>
      </div>
    </div>
  );
}
