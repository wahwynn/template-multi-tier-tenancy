interface Props {
  children: React.ReactNode;
  params: Promise<{ locale: string; slug: string }>;
}

export default async function TenantSlugLayout({ children }: Props) {
  return <>{children}</>;
}
