import { useQuery } from "@tanstack/react-query";
import { LayoutGridIcon, ListIcon, PlusIcon } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router";
import { ProjectCard, ProjectGridCard } from "~/components/project-card";
import { Button } from "~/components/ui/button";
import { projectQueries } from "~/lib/queries";
import { queryClient } from "~/root";
import { metaTitle, pluralize } from "~/utils";
import type { Route } from "./+types/home";

type ProjectsView = "list" | "grid";

function useProjectsView() {
  const [view, setView] = useState<ProjectsView>("list");
  useEffect(() => {
    const stored = localStorage.getItem("dky-projects-view");
    if (stored === "grid" || stored === "list") setView(stored);
  }, []);
  const set = (value: ProjectsView) => {
    setView(value);
    localStorage.setItem("dky-projects-view", value);
  };
  return [view, set] as const;
}

export const meta: Route.MetaFunction = () => [metaTitle("Dashboard")];

export async function clientLoader() {
  await queryClient.ensureQueryData(projectQueries.list());
  return null;
}

function HomeSkeleton() {
  return (
    <section className="mx-auto flex w-full max-w-5xl animate-pulse flex-col gap-6">
      <div className="flex flex-col gap-5 sm:flex-row sm:items-end sm:justify-between">
        <div className="flex flex-col gap-2.5">
          <div className="h-9 w-40 bg-muted" />
          <div className="h-4 w-64 bg-muted" />
        </div>
        <div className="h-9 w-32 bg-muted" />
      </div>
      <div className="flex items-center divide-x divide-border border-y border-border py-3">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="flex flex-1 flex-col gap-1.5 px-5 first:pl-0">
            <div className="h-6 w-10 bg-muted" />
            <div className="h-3 w-16 bg-muted" />
          </div>
        ))}
      </div>
      <div className="divide-y divide-border overflow-hidden border border-border bg-card">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="flex items-center gap-4 px-4 py-4">
            <div className="size-9 flex-none bg-muted" />
            <div className="flex flex-1 flex-col gap-2">
              <div className="h-4 w-40 bg-muted" />
              <div className="h-3 w-24 bg-muted" />
            </div>
            <div className="h-4 w-16 bg-muted" />
          </div>
        ))}
      </div>
    </section>
  );
}

export default function Home() {
  const { data: projects } = useQuery(projectQueries.list());
  const [view, setView] = useProjectsView();

  if (!projects) return <HomeSkeleton />;

  const count = projects.length;

  return (
    <section className="mx-auto flex w-full max-w-5xl flex-col gap-6">
      <div className="flex flex-col gap-5 sm:flex-row sm:items-end sm:justify-between">
        <div className="flex flex-col gap-1.5">
          <h1 className="text-3xl font-bold tracking-tighter md:text-4xl">
            Projects
          </h1>
          <p className="text-sm text-grey">
            {count > 0
              ? `${count} ${pluralize("project", count)} · your deployed apps and services`
              : "Your deployed apps and services live here"}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center border border-input">
            <button
              type="button"
              aria-label="List view"
              aria-pressed={view === "list"}
              onClick={() => setView("list")}
              className={`flex size-8 items-center justify-center transition-colors ${
                view === "list"
                  ? "bg-foreground text-background"
                  : "text-grey hover:text-foreground"
              }`}
            >
              <ListIcon size={15} strokeWidth={1.75} />
            </button>
            <button
              type="button"
              aria-label="Grid view"
              aria-pressed={view === "grid"}
              onClick={() => setView("grid")}
              className={`flex size-8 items-center justify-center transition-colors ${
                view === "grid"
                  ? "bg-foreground text-background"
                  : "text-grey hover:text-foreground"
              }`}
            >
              <LayoutGridIcon size={15} strokeWidth={1.75} />
            </button>
          </div>
          <Link to="/create-project">
            <Button className="gap-1.5">
              <PlusIcon size={15} strokeWidth={2} /> New project
            </Button>
          </Link>
        </div>
      </div>

      {projects && projects.length > 0 && (
        <div className="flex items-center divide-x divide-border border-y border-border py-3">
          {[
            { label: "projects", value: count },
            {
              label: "services",
              value: projects.reduce(
                (sum, p) =>
                  sum + (p.total_services ?? 0) + (p.total_stack_services ?? 0),
                0
              )
            },
            {
              label: "healthy",
              value: projects.reduce(
                (sum, p) =>
                  sum +
                  (p.healthy_services ?? 0) +
                  (p.healthy_stack_services ?? 0),
                0
              )
            },
            {
              label: "environments",
              value: projects.reduce(
                (sum, p) => sum + (p.environments?.length ?? 0),
                0
              )
            }
          ].map((stat) => (
            <div
              key={stat.label}
              className="flex flex-1 flex-col gap-0.5 px-5 first:pl-0"
            >
              <span className="font-mono text-xl font-medium tabular-nums">
                {stat.value}
              </span>
              <span className="text-xs text-grey">{stat.label}</span>
            </div>
          ))}
        </div>
      )}

      {projects && projects.length > 0 ? (
        view === "list" ? (
          <div className="divide-y divide-border overflow-hidden border border-border bg-card shadow-[0_1px_2px_hsl(var(--foreground)/0.04)]">
            {projects.map((project) => (
              <ProjectCard key={project.id} project={project} />
            ))}
          </div>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {projects.map((project) => (
              <ProjectGridCard key={project.id} project={project} />
            ))}
          </div>
        )
      ) : (
        <div className="flex flex-col items-center gap-6 px-6 py-24 text-center">
          <div className="flex flex-col gap-2">
            <h2 className="text-xl font-semibold tracking-tight">
              No projects yet
            </h2>
            <p className="mx-auto max-w-sm text-sm text-grey text-balance">
              Projects group and deploy your services and compose stacks.
            </p>
          </div>
          <Link to="/create-project">
            <Button className="gap-1.5">
              <PlusIcon size={15} strokeWidth={2} /> New project
            </Button>
          </Link>
        </div>
      )}
    </section>
  );
}
