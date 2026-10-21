"use client";

import Link from "next/link";
import { Briefcase, Building2, LayoutDashboard, LineChart, Settings } from "lucide-react";

const links = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/jobs", label: "Jobs", icon: Briefcase },
  { href: "/companies", label: "Companies", icon: Building2 },
  { href: "/analytics", label: "Analytics", icon: LineChart },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function Navbar() {
  return (
    <nav className="w-64 border-r bg-card/50 h-screen sticky top-0 p-6 hidden md:block">
      <div className="flex items-center gap-2 mb-10">
        <div className="h-8 w-8 rounded-lg bg-primary flex items-center justify-center text-primary-foreground font-bold">
          EJA
        </div>
        <span className="font-semibold text-lg">Europe Job Agent</span>
      </div>
      <ul className="space-y-2">
        {links.map((link) => (
          <li key={link.href}>
            <Link
              href={link.href}
              className="flex items-center gap-3 rounded-lg px-3 py-2 text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
            >
              <link.icon className="h-4 w-4" />
              {link.label}
            </Link>
          </li>
        ))}
      </ul>
    </nav>
  );
}
