"use client";

import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { getAnalytics, getJobs } from "@/lib/api";
import { Navbar } from "@/components/navbar";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { JobCard } from "@/components/job-card";
import { UploadResume } from "@/components/upload-resume";
import { Briefcase, Building2, Send, Sparkles } from "lucide-react";

export default function Dashboard() {
  const router = useRouter();
  const { data: analytics, isLoading: analyticsLoading } = useQuery({
    queryKey: ["analytics"],
    queryFn: getAnalytics,
  });

  const { data: jobs, isLoading: jobsLoading } = useQuery({
    queryKey: ["jobs", { min_match_score: 70 }],
    queryFn: () => getJobs({ min_match_score: 70, page_size: 6 }),
  });

  return (
    <div className="flex min-h-screen bg-background">
      <Navbar />
      <main className="flex-1 p-8 max-w-7xl mx-auto w-full">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
            <p className="text-muted-foreground mt-1">
              Your local AI assistant for European DevOps/Platform roles.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <Button variant="outline" onClick={() => router.push("/jobs")}>
              View all jobs
            </Button>
            <Button onClick={() => router.push("/jobs")}>Find matches</Button>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <MetricCard
            title="Active Jobs"
            value={analytics?.total_jobs ?? 0}
            icon={Briefcase}
            loading={analyticsLoading}
          />
          <MetricCard
            title="Companies"
            value={analytics?.total_companies ?? 0}
            icon={Building2}
            loading={analyticsLoading}
          />
          <MetricCard
            title="Applications"
            value={analytics?.total_applications ?? 0}
            icon={Send}
            loading={analyticsLoading}
          />
          <MetricCard
            title="High Matches"
            value={jobs?.total ?? 0}
            icon={Sparkles}
            loading={jobsLoading}
          />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <div className="lg:col-span-2">
            <h2 className="text-xl font-semibold mb-4">Top Matches</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {jobs?.items.map((job) => (
                <JobCard key={job.id} job={job} />
              ))}
              {!jobsLoading && !jobs?.items.length && (
                <div className="col-span-full rounded-xl border border-dashed p-8 text-center text-muted-foreground">
                  <p className="font-medium">No high-match jobs yet.</p>
                  <p className="text-sm mt-1">
                    Upload your resume and run the daily workflow to generate matches.
                  </p>
                </div>
              )}
            </div>
          </div>

          <div className="space-y-6">
            <UploadResume />

            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium text-muted-foreground">Top Countries</CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="space-y-2">
                  {analytics?.top_countries.map((item) => (
                    <li key={item.country} className="flex justify-between text-sm">
                      <span>{item.country}</span>
                      <span className="font-semibold">{item.jobs}</span>
                    </li>
                  ))}
                  {!analytics?.top_countries.length && (
                    <li className="text-sm text-muted-foreground">No data yet.</li>
                  )}
                </ul>
              </CardContent>
            </Card>
          </div>
        </div>
      </main>
    </div>
  );
}

function MetricCard({
  title,
  value,
  icon: Icon,
  loading,
}: {
  title: string;
  value: number;
  icon: React.ElementType;
  loading?: boolean;
}) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
          <Icon className="h-4 w-4" />
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-3xl font-bold">
          {loading ? "—" : value}
        </p>
      </CardContent>
    </Card>
  );
}
