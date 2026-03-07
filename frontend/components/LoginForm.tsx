"use client";

import { useTranslations } from "next-intl";
import { useState, type FormEvent } from "react";

interface Props {
  slug: string;
}

export default function LoginForm({ slug }: Props) {
  const t = useTranslations("auth");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);

    const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "";
    const res = await fetch(`${apiUrl}/t/${slug}/v1/auth/token/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      // simplejwt expects `username` field; our users have email as their username
      body: JSON.stringify({ username: email, password }),
    });

    if (res.ok) {
      window.location.href = `/t/${slug}/dashboard`;
    } else {
      setError(t("invalidCredentials"));
    }
  }

  return (
    <main>
      <h1>{t("login")}</h1>
      <form onSubmit={handleSubmit}>
        <label htmlFor="email">{t("email")}</label>
        <input
          id="email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />
        <label htmlFor="password">{t("password")}</label>
        <input
          id="password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />
        {error && <p role="alert">{error}</p>}
        <button type="submit">{t("login")}</button>
      </form>
    </main>
  );
}
