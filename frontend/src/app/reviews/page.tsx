"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { Annotation, Page } from "@/lib/types";
import { ConfidenceBadge } from "@/components/ConfidenceBadge";

export default function ReviewQueuePage() {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery<Page<Annotation>>({
    queryKey: ["review-queue"],
    queryFn: () => api.reviewQueue(),
  });

  const decide = useMutation({
    mutationFn: ({ id, decision }: { id: string; decision: string }) =>
      api.submitReview(id, { decision }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["review-queue"] }),
  });

  return (
    <div>
      <h2 className="text-2xl font-bold mb-6">Review Queue</h2>
      {isLoading && <p className="text-gray-500">Loading…</p>}
      {data?.items.length === 0 && (
        <p className="text-gray-500">Queue is empty — nothing needs human review.</p>
      )}
      <div className="space-y-3">
        {data?.items.map((a) => (
          <div
            key={a.id}
            className="rounded-lg bg-white border border-gray-200 p-4 flex items-center justify-between"
          >
            <div>
              <div className="flex items-center gap-2">
                <span className="font-medium">Image {a.image_id.slice(0, 8)}</span>
                <ConfidenceBadge status={a.status} />
                <span className="text-xs text-gray-500">
                  conf {(a.confidence as any)?.overall ?? "—"} · {a.detections.length} det
                </span>
              </div>
              {a.caption && <p className="text-sm text-gray-600 mt-1">{a.caption}</p>}
              <div className="mt-1 flex flex-wrap gap-1">
                {a.detections.map((d, i) => (
                  <span key={i} className="rounded bg-gray-100 px-2 py-0.5 text-xs">
                    {d.label} {(d.confidence ?? d.score).toFixed(2)}
                  </span>
                ))}
              </div>
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => decide.mutate({ id: a.id, decision: "approve" })}
                className="rounded-md bg-ok px-3 py-1.5 text-sm text-white"
              >
                Approve
              </button>
              <button
                onClick={() => decide.mutate({ id: a.id, decision: "reject" })}
                className="rounded-md bg-danger px-3 py-1.5 text-sm text-white"
              >
                Reject
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
