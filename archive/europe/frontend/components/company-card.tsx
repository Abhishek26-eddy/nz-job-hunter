import { Company } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

interface CompanyCardProps {
  company: Company;
}

export function CompanyCard({ company }: CompanyCardProps) {
  return (
    <Card data-testid="company-card" className="hover:shadow-md transition-shadow">
      <CardHeader className="pb-3">
        <CardTitle className="text-lg font-semibold">{company.name}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        <p className="text-sm text-muted-foreground">
          {company.country?.name} {company.city ? `• ${company.city}` : ""}
        </p>
        <div className="flex flex-wrap gap-2">
          {company.industry && <Badge variant="secondary">{company.industry}</Badge>}
          <Badge variant="outline">{company.visa_sponsorship}</Badge>
        </div>
      </CardContent>
    </Card>
  );
}
