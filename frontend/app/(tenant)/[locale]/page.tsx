import Link from "next/link";

export default function HomePage() {
  return (
    <main>
      <h1>Welcome</h1>
      <Link href="/login">Sign in</Link>
    </main>
  );
}
