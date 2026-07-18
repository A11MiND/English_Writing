import { WritingEditor } from "@/components/writing-editor";

type PageProps = {
  params: Promise<{ taskId: string }>;
};

export default async function StudentExamPage({ params }: PageProps) {
  const { taskId } = await params;
  return <WritingEditor taskId={taskId} expectedMode="EXAM" />;
}
