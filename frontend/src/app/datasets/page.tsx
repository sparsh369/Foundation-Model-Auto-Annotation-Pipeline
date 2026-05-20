"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { Dataset, Page } from "@/lib/types";

export default function DatasetsPage() {
  const { data, isLoading } = useQuery<Page<Dataset>>({
    queryKey: ["datasets"],
    queryFn: () => api.listDatasets(),
  });

  return (
    <div>
      <h2 className="text-2xl font-bold mb-6">Datasets</h2>
      {isLoading && <p className="text-gray-500">Loading…</p>}
      <div className="grid grid-cols-3 gap-4">
        {data?.items.map((d) => (
          <div key={d.id} className="rounded-lg bg-white border border-gray-200 p-5">
            <h3 className="font-semibold">{d.name}</h3>
            <p className="text-sm text-gray-500 mt-1">{d.description ?? "No description"}</p>
            <div className="mt-3 flex justify-between text-sm">
              <span>{d.image_count} images</span>
              <span className="text-gray-500">{d.status}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
