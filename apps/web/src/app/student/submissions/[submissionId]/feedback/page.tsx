import { redirect } from "next/navigation";

export default async function LegacyStudentFeedbackPage({ params }: { params: Promise<{ submissionId: string }> }) {
  const { submissionId } = await params;
  redirect(`/student/feedback/${submissionId}`);
}
