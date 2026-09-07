import { Suspense } from "react";

import { StudentHome } from "@/components/student-home";

export default function StudentWritingPage() {
  return (
    <Suspense fallback={<main className="loading-state">Loading student writing...</main>}>
      <StudentHome />
    </Suspense>
  );
}
