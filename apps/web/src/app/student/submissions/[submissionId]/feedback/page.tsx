import { StudentFeedback } from "@/components/student-feedback";

export default async function StudentFeedbackPage({
  params,
}: {
  params: Promise<{ submissionId: string }>;
}) {
  const { submissionId } = await params;
  return <StudentFeedback submissionId={submissionId} />;
}
