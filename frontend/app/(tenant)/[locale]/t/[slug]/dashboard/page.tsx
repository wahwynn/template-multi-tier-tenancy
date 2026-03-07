interface Props {
  params: Promise<{ locale: string; slug: string }>;
}

export default async function DashboardPage({ params }: Props) {
  const { slug } = await params;

  return (
    <main>
      <h1>Dashboard</h1>
      <p>Tenant: {slug}</p>
    </main>
  );
}
