import LoginForm from "@/components/LoginForm";

interface Props {
  params: Promise<{ locale: string; slug: string }>;
}

export default async function LoginPage({ params }: Props) {
  const { slug } = await params;
  return <LoginForm slug={slug} />;
}
