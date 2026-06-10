import { ArrowLeftIcon } from "lucide-react";
import type * as React from "react";
import { Link, NavLink } from "react-router";
import { Card } from "~/components/ui/card";
import { cn } from "~/lib/utils";

const GROUPS = [
  {
    label: "Account",
    links: [
      { to: "/settings", label: "Registry credentials", end: true },
      { to: "/settings/ssh-keys", label: "SSH keys", end: false }
    ]
  },
  {
    label: "Integrations",
    links: [{ to: "/settings/git-apps", label: "Git apps", end: false }]
  }
];

export function SettingsNav() {
  return (
    <nav className="flex flex-col gap-6">
      {GROUPS.map((group) => (
        <div key={group.label} className="flex flex-col gap-1">
          <p className="mb-1 px-3 text-[11px] font-medium uppercase tracking-[0.18em] text-grey">
            {group.label}
          </p>
          {group.links.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              end={link.end}
              className={({ isActive }) =>
                cn(
                  "flex items-center px-3 py-2 text-sm transition-colors duration-150",
                  isActive
                    ? "bg-foreground font-medium text-background"
                    : "text-grey hover:bg-muted hover:text-foreground"
                )
              }
            >
              {link.label}
            </NavLink>
          ))}
        </div>
      ))}
    </nav>
  );
}

export function SettingsLayout({
  title,
  description,
  children
}: {
  title: string;
  description: string;
  children: React.ReactNode;
}) {
  return (
    <div className="mx-auto w-full max-w-5xl">
      <Link
        to="/"
        className="mb-8 inline-flex w-fit items-center gap-1.5 text-[11px] font-medium uppercase tracking-[0.18em] text-grey transition-colors duration-150 hover:text-foreground"
      >
        <ArrowLeftIcon size={12} strokeWidth={2} /> Projects
      </Link>

      <div className="flex flex-col gap-8 md:flex-row md:gap-12">
        <aside className="md:w-52 md:shrink-0 md:self-start lg:sticky lg:top-20">
          <SettingsNav />
        </aside>

        <div className="flex min-w-0 max-w-3xl flex-1 flex-col gap-8">
          <header className="flex flex-col gap-1.5">
            <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">
              {title}
            </h1>
            <p className="text-sm text-grey">{description}</p>
          </header>
          {children}
        </div>
      </div>
    </div>
  );
}

export function SettingsSection({
  title,
  description,
  action,
  children,
  className
}: {
  title: string;
  description?: string;
  action?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <Card className={cn("overflow-hidden", className)}>
      <div className="flex items-start justify-between gap-4 border-b border-border px-5 py-4">
        <div className="flex min-w-0 flex-col gap-0.5">
          <h2 className="font-semibold tracking-tight">{title}</h2>
          {description && (
            <p className="text-[13px] text-grey">{description}</p>
          )}
        </div>
        {action && <div className="flex-none">{action}</div>}
      </div>
      {children}
    </Card>
  );
}

export function SettingsRows({ children }: { children: React.ReactNode }) {
  return <div className="divide-y divide-border">{children}</div>;
}

export function SettingsRow({
  tile,
  tileNeutral,
  primary,
  secondary,
  right
}: {
  tile: React.ReactNode;
  // Ink monogram tile by default; neutral surface for real brand marks
  // (provider logos stay unpainted).
  tileNeutral?: boolean;
  primary: React.ReactNode;
  secondary?: React.ReactNode;
  right?: React.ReactNode;
}) {
  return (
    <div className="flex items-center gap-3 px-5 py-3.5 transition-colors duration-150 hover:bg-muted/40">
      <span
        className={cn(
          "flex size-9 flex-none items-center justify-center",
          tileNeutral
            ? "bg-foreground/[0.04] text-foreground ring-1 ring-border"
            : "bg-foreground text-background"
        )}
      >
        {tile}
      </span>
      <div className="flex min-w-0 flex-1 flex-col gap-0.5">
        <div className="flex min-w-0 items-center gap-2">{primary}</div>
        {secondary && (
          <div className="truncate font-mono text-xs text-grey">
            {secondary}
          </div>
        )}
      </div>
      {right && (
        <div className="flex flex-none items-center gap-2">{right}</div>
      )}
    </div>
  );
}

export function SettingsFormFooter({
  label,
  children
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-4 border-t border-border bg-muted/25 px-5 py-5">
      <h3 className="text-[11px] font-medium uppercase tracking-[0.16em] text-grey">
        {label}
      </h3>
      {children}
    </div>
  );
}

export function SettingsEmpty({
  title,
  hint,
  glyph
}: {
  title: string;
  hint: string;
  // Oversized muted mono word of the section's noun, sitting behind the copy.
  glyph?: string;
}) {
  return (
    <div className="relative flex flex-col items-center gap-2 overflow-hidden px-6 py-14 text-center">
      {glyph && (
        <span
          aria-hidden
          className="pointer-events-none absolute inset-0 flex select-none items-center justify-center font-mono text-[7rem] font-semibold uppercase leading-none tracking-tight text-foreground/[0.04]"
        >
          {glyph}
        </span>
      )}
      <p className="relative font-medium tracking-tight">{title}</p>
      <p className="relative mx-auto max-w-xs text-sm text-grey">{hint}</p>
    </div>
  );
}
