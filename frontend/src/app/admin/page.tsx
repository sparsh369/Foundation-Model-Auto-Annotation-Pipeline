"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

interface AuditEntry {
  id: string;
  actor_id: string | null;
  action: string;
  entity_type: string;
  entity_id: string | null;
  created_at: string;
}

export default function AdminPage() {
  const { data } = useQuery<AuditEntry[]>({ queryKey: ["audit"], queryFn: () => api.audit() });

  return (
    <div>
      <h2 className="text-2xl font-bold mb-6">Admin · Audit Log</h2>
      <div className="rounded-lg bg-white border border-gray-200">
        <table className="w-full text-sm">
          <thead className="text-left text-gray-500">
            <tr>
              <th className="px-5 py-2">Time</th>
              <th className="px-5 py-2">Action</th>
              <th className="px-5 py-2">Entity</th>
              <th className="px-5 py-2">Actor</th>
            </tr>
          </thead>
          <tbody>
            {data?.map((e) => (
              <tr key={e.id} className="border-t">
                <td className="px-5 py-2 text-gray-500">
                  {new Date(e.created_at).toLocaleString()}
                </td>
                <td className="px-5 py-2 font-medium">{e.action}</td>
                <td className="px-5 py-2">
                  {e.entity_type}/{e.entity_id?.slice(0, 8)}
                </td>
                <td className="px-5 py-2 text-gray-500">{e.actor_id?.slice(0, 8) ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
