import { PersonalPracticeResultPage } from "@/components/personal-practice-result";

type PageProps = { params: Promise<{ taskId: string }> };

export default async function StudentPracticeResultRoute({ params }: PageProps) {
  const { taskId } = await params;
  return <PersonalPracticeResultPage taskId={taskId} />;
}
