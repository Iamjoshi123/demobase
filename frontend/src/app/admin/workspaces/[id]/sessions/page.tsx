import { redirect } from "next/navigation";

export default function LegacyWorkspaceSessionsPage({
  params,
  searchParams,
}: {
  params: { id: string };
  searchParams?: { session?: string };
}) {
  const session = searchParams?.session ? `&session=${encodeURIComponent(searchParams.session)}` : "";
  redirect(`/admin/sessions?workspaceId=${encodeURIComponent(params.id)}${session}`);
}
