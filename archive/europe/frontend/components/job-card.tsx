"use client";

import { useState } from "react";
import { Job } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { CheckCircle2, ChevronDown, ChevronUp, MapPin } from "lucide-react";

interface JobCardProps {
  job: Job;
}

export function JobCard({ job }: JobCardProps) {
  return (
    <div data-testid="job-card">
      <JobCardContent job={job} />
    </div>
  );
}

function JobCardContent({ job }: JobCardProps) {
  const [expanded, setExpanded] = useState(false);
  const score = job.match_score ?? 0;
  const scoreColor =
    score >= 85 ? "bg-emerald-500" : score >= 70 ? "bg-amber-500" : "bg-slate-400";

  return (
    <Card className="hover:shadow-md transition-shadow h-full flex flex-col">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <CardTitle className="text-lg font-semibold leading-tight truncate">
              {job.title}
            </CardTitle>
            <p className="text-sm text-muted-foreground mt-1 flex items-center gap-1">
              <span className="font-medium text-foreground truncate">{job.company?.name}</span>
              <span className="text-muted-foreground">•</span>
              <MapPin className="h-3 w-3 shrink-0" />
              <span className="truncate">{job.location || "Remote"}</span>
            </p>
          </div>
          <div
            className={`h-10 w-10 rounded-full ${scoreColor} flex items-center justify-center text-white text-xs font-bold shrink-0`}
            title={`Match score: ${Math.round(score)}`}
          >
            {Math.round(score)}
          </div>
        </div>
        {job.application_status && (
          <div className="mt-2 inline-flex w-fit items-center gap-1 rounded-full bg-emerald-100 dark:bg-emerald-950 px-2.5 py-1 text-xs font-medium text-emerald-700 dark:text-emerald-400">
            <CheckCircle2 className="h-3 w-3" />
            {job.application_status === "applied" ? "Applied" : job.application_status.replace(/_/g, " ")}
          </div>
        )}
      </CardHeader>
      <CardContent className="space-y-3 flex-1 flex flex-col">
        <div className="flex flex-wrap gap-2">
          {job.workplace_type && (
            <Badge variant="secondary">{job.workplace_type}</Badge>
          )}
          <Badge variant="outline">{job.visa_sponsorship_inferred}</Badge>
          {job.salary_estimate && (
            <Badge variant="outline">{job.salary_estimate}</Badge>
          )}
          {job.role_category && (
            <Badge variant="outline">{job.role_category}</Badge>
          )}
        </div>

        {job.should_apply && (
          <p className="text-xs font-medium text-green-600 dark:text-green-400">
            AI recommends applying
          </p>
        )}

        <div className="mt-auto pt-2">
          <Button
            variant="ghost"
            size="sm"
            className="h-auto px-0 py-0 text-muted-foreground hover:text-foreground"
            onClick={() => setExpanded((v) => !v)}
          >
            {expanded ? (
              <>
                Hide reason <ChevronUp className="h-3 w-3 ml-1" />
              </>
            ) : (
              <>
                Why this match <ChevronDown className="h-3 w-3 ml-1" />
              </>
            )}
          </Button>
          {expanded && (
            <div className="text-sm text-muted-foreground mt-2 space-y-2 animate-in fade-in slide-in-from-top-1">
              {job.match_reason && <p>{job.match_reason}</p>}
              {job.score_breakdown && (
                <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
                  {Object.entries(job.score_breakdown).map(([key, value]) => (
                    <div key={key} className="flex justify-between">
                      <span className="capitalize">{key.replace(/_/g, " ")}</span>
                      <span className="font-medium text-foreground">{value}</span>
                    </div>
                  ))}
                </div>
              )}
              {job.critical_missing_skills && job.critical_missing_skills.length > 0 && (
                <p>
                  <span className="font-medium text-foreground">Critical missing skills:</span>{" "}
                  {job.critical_missing_skills.join(", ")}
                </p>
              )}
              {job.missing_skills && job.missing_skills.length > 0 && (
                <p>
                  <span className="font-medium text-foreground">Missing skills:</span>{" "}
                  {job.missing_skills.join(", ")}
                </p>
              )}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
