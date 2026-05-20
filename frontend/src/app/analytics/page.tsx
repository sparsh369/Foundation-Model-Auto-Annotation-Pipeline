"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

// Placeholder analytics — wire to a /analytics aggregation endpoint in production.
const sample = [
  { bucket: "0.0–0.2", count: 12 },
  { bucket: "0.2–0.5", count: 84 },
  { bucket: "0.5–0.85", count: 240 },
  { bucket: "0.85–1.0", count: 1320 },
];

export default function AnalyticsPage() {
  return (
    <div>
      <h2 className="text-2xl font-bold mb-6">Analytics</h2>
      <div className="rounded-lg bg-white border border-gray-200 p-5">
        <h3 className="font-medium mb-4">Confidence distribution</h3>
        <div style={{ height: 320 }}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={sample}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="bucket" />
              <YAxis />
              <Tooltip />
              <Bar dataKey="count" fill="#4f46e5" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
