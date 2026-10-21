"use client";

import { useQuery } from "@tanstack/react-query";
import { getAnalytics } from "@/lib/api";
import { Navbar } from "@/components/navbar";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function AnalyticsPage() {
  const { data } = useQuery({
    queryKey: ["analytics"],
    queryFn: getAnalytics,
  });

  return (
    <div className="flex min-h-screen">
      <Navbar />
      <main className="flex-1 p-8">
        <h1 className="text-3xl font-bold mb-8">Analytics</h1>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
          <MetricCard title="Total Jobs" value={data?.total_jobs ?? 0} />
          <MetricCard title="Companies Tracked" value={data?.total_companies ?? 0} />
          <MetricCard title="Applications" value={data?.total_applications ?? 0} />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card>
            <CardHeader>
              <CardTitle>Application Status</CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="space-y-2">
                {Object.entries(data?.status_counts ?? {}).map(([status, count]) => (
                  <li key={status} className="flex justify-between text-sm">
                    <span className="capitalize">{status.replace(/_/g, " ")}</span>
                    <span className="font-semibold">{count}</span>
                  </li>
                ))}
                {!Object.keys(data?.status_counts ?? {}).length && (
                  <li className="text-muted-foreground">No applications yet.</li>
                )}
              </ul>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Top Countries</CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="space-y-2">
                {data?.top_countries.map((item) => (
                  <li key={item.country} className="flex justify-between text-sm">
                    <span>{item.country}</span>
                    <span className="font-semibold">{item.jobs} jobs</span>
                  </li>
                ))}
                {!data?.top_countries.length && (
                  <li className="text-muted-foreground">No data yet.</li>
                )}
              </ul>
            </CardContent>
          </Card>
        </div>
      </main>
    </div>
  );
}

function MetricCard({ title, value }: { title: string; value: number }) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-3xl font-bold">{value}</p>
      </CardContent>
    </Card>
  );
}
