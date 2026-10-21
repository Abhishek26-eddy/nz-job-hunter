"use client";

import { useQuery } from "@tanstack/react-query";
import { getCompanies } from "@/lib/api";
import { Navbar } from "@/components/navbar";
import { CompanyCard } from "@/components/company-card";

export default function CompaniesPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["companies"],
    queryFn: () => getCompanies({ page_size: 50 }),
  });

  return (
    <div className="flex min-h-screen">
      <Navbar />
      <main className="flex-1 p-8">
        <h1 className="text-3xl font-bold mb-2">Companies</h1>
        <p className="text-muted-foreground mb-8">
          European companies hiring DevOps and Platform engineers.
        </p>

        {isLoading && <p>Loading companies...</p>}

        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
          {data?.items.map((company) => (
            <CompanyCard key={company.id} company={company} />
          ))}
        </div>
      </main>
    </div>
  );
}
