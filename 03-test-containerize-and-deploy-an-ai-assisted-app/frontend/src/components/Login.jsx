import { useState } from "react";
import { login } from "../api/auth";

/** Password gate shown until a valid session cookie is established. */
export default function Login({ message, onSuccess }) {
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await login(password);
      onSuccess();
    } catch (err) {
      setError(err.message ?? "Couldn't log in.");
      setPassword("");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="login-screen">
      <form className="modal login-form" onSubmit={handleSubmit}>
        <h1>Card Catalog</h1>
        <p className="app-subtitle">Access Card Required</p>

        {message && <p className="login-message">{message}</p>}

        <label>
          Password
          <input
            type="password"
            autoFocus
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Enter password"
          />
        </label>

        {error && <p className="form-error">{error}</p>}

        <div className="form-actions">
          <button type="submit" disabled={submitting || !password}>
            {submitting ? "Checking…" : "Enter"}
          </button>
        </div>
      </form>
    </div>
  );
}
