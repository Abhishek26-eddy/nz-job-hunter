"use client";

import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { createApplication, getJobs } from "@/lib/api";
import { Navbar } from "@/components/navbar";
import { JobCard } from "@/components/job-card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { ExternalLink, CheckCircle, Filter, Search } from "lucide-react";

export default function JobsPage() {
  const [input, setInput] = useState("");
  const [search, setSearch] = useState("");
  const [countryCode, setCountryCode] = useState("");
  const [onlyWorthApplying, setOnlyWorthApplying] = useState(false);
  const queryClient = useQueryClient();

  useEffect(() => {
    const timer = setTimeout(() => setSearch(input), 250);
    return () => clearTimeout(timer);
  }, [input]);

  const { data, isLoading } = useQuery({
    queryKey: ["jobs", { search, country_code: countryCode, should_apply: onlyWorthApplying || undefined }],
    queryFn: () =>
      getJobs({
        search,
        country_code: countryCode,
        should_apply: onlyWorthApplying ? true : undefined,
        page_size: 50,
      }),
  });

  const applyMutation = useMutation({
    mutationFn: (jobId: number) => createApplication({ job_id: jobId, status: "applied" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["jobs"] });
      queryClient.invalidateQueries({ queryKey: ["analytics"] });
    },
  });

  return (
    <div className="flex min-h-screen bg-background">
      <Navbar />
      <main className="flex-1 p-8 max-w-7xl mx-auto w-full">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Jobs worth applying to</h1>
            <p className="text-muted-foreground mt-1">
              Crawled, filtered for Europe, matched to your resume, and ranked by AI.
            </p>
          </div>
          <Button
            variant={onlyWorthApplying ? "default" : "outline"}
            onClick={() => setOnlyWorthApplying((v) => !v)}
          >
            <Filter className="h-4 w-4 mr-2" />
            {onlyWorthApplying ? "AI recommends applying" : "All jobs"}
          </Button>
        </div>

        <div className="flex flex-wrap items-center gap-3 mb-6">
          <div className="relative max-w-md flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search title, company, skill..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              className="pl-9"
            />
          </div>
          <Input
            placeholder="Country code (e.g. DE)"
            value={countryCode}
            onChange={(e) => setCountryCode(e.target.value)}
            className="max-w-[10rem]"
          />
        </div>

        {onlyWorthApplying && (
          <div className="mb-6">
            <Badge variant="secondary" className="text-sm">
              Filter: AI recommends applying
            </Badge>
          </div>
        )}

        {isLoading && <p className="text-muted-foreground">Loading jobs...</p>}

        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {data?.items.map((job) => (
            <div key={job.id} className="flex flex-col gap-3">
              <JobCard job={job} />
              <div className="flex gap-2">
                {job.application_url ? (
                  <a
                    href={job.application_url}
                    target="_blank"
                    rel="noreferrer"
                    className={cn(
                      "inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors",
                      "border border-input bg-background hover:bg-accent hover:text-accent-foreground",
                      "h-9 px-4 py-2 flex-1"
                    )}
                  >
                    <ExternalLink className="w-4 h-4 mr-2" />
                    Open application
                  </a>
                ) : (
                  <Button variant="outline" className="flex-1" disabled>
                    No application URL
                  </Button>
                )}
                <Button
                  className="flex-1"
                  variant={job.application_status ? "outline" : "default"}
                  onClick={() => applyMutation.mutate(job.id)}
                  disabled={
                    !!job.application_status ||
                    (applyMutation.isPending && applyMutation.variables === job.id)
                  }
                >
                  <CheckCircle className="w-4 h-4 mr-2" />
                  {job.application_status ? "Applied" : "Mark applied"}
                </Button>
              </div>
            </div>
          ))}
        </div>

        {!isLoading && data?.items.length === 0 && (
          <div className="mt-12 text-center text-muted-foreground">
            <p>No jobs match the current filters.</p>
            <p className="text-sm mt-1">
              Try turning off the AI filter or uploading a master resume and re-running the daily crawl.
            </p>
          </div>
        )}
      </main>
    </div>
  );
}
