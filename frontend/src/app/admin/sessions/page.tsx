import { Suspense } from "react";

import { AdminSessionsClient } from "./sessions-client";

export default function AdminSessionsPage() {
  return (
    <Suspense fallback={null}>
      <AdminSessionsClient />
    </Suspense>
  );
}
