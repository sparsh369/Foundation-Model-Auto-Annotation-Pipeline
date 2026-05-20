"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { Dataset, Page } from "@/lib/types";

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-lg bg-white border border-gray-200 p-5">
      <p className="text-sm text-gray-500">{label}</p>
      <p className="mt-1 text-2xl font-semibold">{value}</p>
    </div>
  );
}

export default function DashboardPage() {
  const { data, isLoading } = useQuery<Page<Dataset>>({
    queryKey: ["datasets"],
    queryFn: () => api.listDatasets(),
  });

  const totalImages =
    data?.items.reduce((acc, d) => acc + d.image_count, 0) ?? 0;

  return (
    <div>
      <h2 className="text-2xl font-bold mb-6">Dashboard</h2>
      <div className="grid grid-cols-4 gap-4 mb-8">
        <Stat label="Datasets" value={isLoading ? "…" : data?.total ?? 0} />
        <Stat label="Total images" value={isLoading ? "…" : totalImages} />
        <Stat label="Auto-label rate" value="—" />
        <Stat label="Pending review" value="—" />
      </div>

      <div className="rounded-lg bg-white border border-gray-200">
        <div className="border-b px-5 py-3 font-medium">Recent datasets</div>
        <table className="w-full text-sm">
          <thead className="text-left text-gray-500">
            <tr>
              <th className="px-5 py-2">Name</th>
              <th className="px-5 py-2">Images</th>
              <th className="px-5 py-2">Status</th>
              <th className="px-5 py-2">Created</th>
            </tr>
          </thead>
          <tbody>
            {data?.items.map((d) => (
              <tr key={d.id} className="border-t hover:bg-gray-50">
                <td className="px-5 py-2 font-medium">{d.name}</td>
                <td className="px-5 py-2">{d.image_count}</td>
                <td className="px-5 py-2">{d.status}</td>
                <td className="px-5 py-2 text-gray-500">
                  {new Date(d.created_at).toLocaleDateString()}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
