"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Navbar } from "@/components/navbar";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { UploadResume } from "@/components/upload-resume";
import { listResumes } from "@/lib/api";
import { FileText } from "lucide-react";

export default function SettingsPage() {
  const [openaiKey, setOpenaiKey] = useState("");
  const [slackUrl, setSlackUrl] = useState("");
  const { data: resumes, isLoading } = useQuery({
    queryKey: ["resumes"],
    queryFn: listResumes,
  });
  const masterResume = resumes?.find((r) => r.is_master);

  return (
    <div className="flex min-h-screen">
      <Navbar />
      <main className="flex-1 p-8">
        <h1 className="text-3xl font-bold mb-8">Settings</h1>

        <div className="max-w-2xl space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Resume</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {isLoading ? (
                <p className="text-sm text-muted-foreground">Loading resume...</p>
              ) : masterResume ? (
                <div className="flex items-start gap-3">
                  <FileText className="h-5 w-5 text-muted-foreground mt-0.5" />
                  <div>
                    <p className="font-medium">{masterResume.name}</p>
                    <p className="text-sm text-muted-foreground">
                      Master resume uploaded{" "}
                      {new Date(masterResume.updated_at).toLocaleString()}
                    </p>
                  </div>
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">
                  No master resume uploaded yet. Upload one so the AI pipeline can match you against jobs.
                </p>
              )}
              <UploadResume />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>AI Configuration</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="openai">OpenAI API Key</Label>
                <Input
                  id="openai"
                  type="password"
                  placeholder="sk-..."
                  value={openaiKey}
                  onChange={(e) => setOpenaiKey(e.target.value)}
                />
                <p className="text-sm text-muted-foreground">
                  Used for optional advanced features; the local pipeline runs without it.
                </p>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Notifications</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="slack">Slack Webhook URL</Label>
                <Input
                  id="slack"
                  placeholder="https://hooks.slack.com/services/..."
                  value={slackUrl}
                  onChange={(e) => setSlackUrl(e.target.value)}
                />
              </div>
              <Button>Save Changes</Button>
            </CardContent>
          </Card>
        </div>
      </main>
    </div>
  );
}
