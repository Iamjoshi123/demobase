import { redirect } from "next/navigation";

export default function LegacyWorkspacePage({ params }: { params: { id: string } }) {
  redirect(`/admin/products/${params.id}`);
}
