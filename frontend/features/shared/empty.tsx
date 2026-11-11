import { Leaf } from "lucide-react";

export function Empty({ text }: { text: string }) {
  return (
    <div className="empty">
      <Leaf />
      <p>{text}</p>
    </div>
  );
}
