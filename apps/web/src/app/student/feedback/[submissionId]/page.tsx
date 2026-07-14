import { StudentFeedback } from "@/components/student-feedback";

export default async function StudentFeedbackRoute({
  params,
}: {
  params: Promise<{ submissionId: string }>;
}) {
  const { submissionId } = await params;
  return <StudentFeedback submissionId={submissionId} />;
}
