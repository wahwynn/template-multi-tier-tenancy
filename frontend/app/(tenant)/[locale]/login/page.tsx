import { headers } from "next/headers";
import { notFound } from "next/navigation";
import LoginForm from "@/components/LoginForm";
import { getTenantSlugFromHostname } from "@/lib/tenant";

export default async function LoginPage() {
  const host = (await headers()).get("host") ?? "";
  const slug = getTenantSlugFromHostname(host);

  if (!slug) notFound();

  return <LoginForm slug={slug} />;
}
