"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { Dataset, Page } from "@/lib/types";

export default function JobsPage() {
  const { data } = useQuery<Page<Dataset>>({
    queryKey: ["datasets"],
    queryFn: () => api.listDatasets(),
  });

  return (
    <div>
      <h2 className="text-2xl font-bold mb-6">Jobs</h2>
      <p className="text-gray-600 mb-4 text-sm">
        Launch an auto-annotation job against a dataset. The pipeline fans out across the
        GPU worker pool; progress updates appear here.
      </p>
      <div className="rounded-lg bg-white border border-gray-200 p-5">
        <h3 className="font-medium mb-3">Start auto-annotation</h3>
        <form
          onSubmit={async (e) => {
            e.preventDefault();
            const fd = new FormData(e.currentTarget);
            await api.createJob({
              dataset_id: String(fd.get("dataset_id")),
              type: "auto_annotate",
              params: {
                prompts: String(fd.get("prompts"))
                  .split(",")
                  .map((s) => s.trim())
                  .filter(Boolean),
                enable_segmentation: true,
                enable_vlm: true,
              },
            });
            alert("Job queued");
          }}
          className="space-y-3"
        >
          <select name="dataset_id" className="w-full rounded-md border px-3 py-2 text-sm">
            {data?.items.map((d) => (
              <option key={d.id} value={d.id}>
                {d.name} ({d.image_count} images)
              </option>
            ))}
          </select>
          <input
            name="prompts"
            placeholder="Open-vocab prompts, comma-separated (e.g. car, person, traffic light)"
            className="w-full rounded-md border px-3 py-2 text-sm"
          />
          <button className="rounded-md bg-brand px-4 py-2 text-sm text-white">
            Queue job
          </button>
        </form>
      </div>
    </div>
  );
}
