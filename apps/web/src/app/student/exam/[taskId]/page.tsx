import { redirect } from "next/navigation";

export default async function LegacyStudentExamPage({ params }: { params: Promise<{ taskId: string }> }) {
  const { taskId } = await params;
  redirect(`/student/tasks/${taskId}/exam`);
}
