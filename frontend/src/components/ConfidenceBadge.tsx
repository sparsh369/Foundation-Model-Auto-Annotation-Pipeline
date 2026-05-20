import clsx from "clsx";

const MAP: Record<string, { label: string; cls: string }> = {
  auto_approved: { label: "Auto-approved", cls: "bg-green-100 text-ok" },
  human_approved: { label: "Approved", cls: "bg-green-100 text-ok" },
  needs_review: { label: "Needs review", cls: "bg-amber-100 text-warn" },
  rejected: { label: "Rejected", cls: "bg-red-100 text-danger" },
  human_corrected: { label: "Corrected", cls: "bg-indigo-100 text-brand" },
};

export function ConfidenceBadge({ status }: { status: string }) {
  const v = MAP[status] ?? { label: status, cls: "bg-gray-100 text-gray-600" };
  return (
    <span className={clsx("rounded-full px-2.5 py-0.5 text-xs font-medium", v.cls)}>
      {v.label}
    </span>
  );
}
