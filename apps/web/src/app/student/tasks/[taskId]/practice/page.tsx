import { WritingEditor } from "@/components/writing-editor";

type PageProps = {
  params: Promise<{ taskId: string }>;
};

export default async function PracticeWritingPage({ params }: PageProps) {
  const { taskId } = await params;
  return <WritingEditor taskId={taskId} expectedMode="PRACTICE" />;
}
