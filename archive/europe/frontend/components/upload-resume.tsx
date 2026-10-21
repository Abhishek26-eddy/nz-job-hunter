"use client";

import { useState, useRef } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { uploadResume, runMatching } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Upload, FileText } from "lucide-react";

export function UploadResume() {
  const [fileName, setFileName] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: (file: File) => uploadResume(file),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["jobs"] });
      queryClient.invalidateQueries({ queryKey: ["analytics"] });
      runMatching().then(() => {
        queryClient.invalidateQueries({ queryKey: ["jobs"] });
        queryClient.invalidateQueries({ queryKey: ["analytics"] });
      });
    },
  });

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setFileName(file.name);
    mutation.mutate(file);
  };

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base font-medium">Master Resume</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <p className="text-sm text-muted-foreground">
          Upload your resume so the local AI pipeline can match you against crawled jobs.
        </p>
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,.txt,.md,.doc,.docx"
          className="hidden"
          onChange={handleChange}
        />
        <Button
          variant="outline"
          className="w-full"
          onClick={() => inputRef.current?.click()}
          disabled={mutation.isPending}
        >
          {mutation.isPending ? (
            "Uploading..."
          ) : fileName ? (
            <>
              <FileText className="h-4 w-4 mr-2" />
              {fileName}
            </>
          ) : (
            <>
              <Upload className="h-4 w-4 mr-2" />
              Upload resume
            </>
          )}
        </Button>
        {mutation.isError && (
          <p className="text-xs text-red-500">Upload failed. Please try again.</p>
        )}
      </CardContent>
    </Card>
  );
}
