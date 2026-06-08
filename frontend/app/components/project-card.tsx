import { ChevronRightIcon, SettingsIcon } from "lucide-react";
import { Link, useNavigate } from "react-router";
import type { ApiResponse } from "~/api/client";
import { Ping } from "~/components/ping";
import type { StatusBadgeColor } from "~/components/status-badge";
import { pluralize } from "~/utils";

type Project = ApiResponse<"get", "/api/projects/">[number];

function timeAgo(value: string) {
  const seconds = Math.max(
    0,
    Math.floor((Date.now() - new Date(value).getTime()) / 1000)
  );
  if (seconds < 60) return "just now";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `${days}d ago`;
  const months = Math.floor(days / 30);
  return `${months}mo ago`;
}

export function ProjectCard({ project }: { project: Project }) {
  const navigate = useNavigate();
  const healthy =
    (project.healthy_services ?? 0) + (project.healthy_stack_services ?? 0);
  const total =
    (project.total_services ?? 0) + (project.total_stack_services ?? 0);

  let color: StatusBadgeColor = "gray";
  if (total > 0) {
    color = healthy === total ? "green" : healthy === 0 ? "red" : "yellow";
  }

  const envs = project.environments ?? [];
  const shownEnvs = envs.slice(0, 3);
  const overflow = envs.length - shownEnvs.length;

  return (
    <Link
      to={`/project/${project.slug}/production`}
      className="group grid grid-cols-[1fr_auto] items-center gap-4 px-5 py-4 transition-colors duration-150 hover:bg-muted/40 focus-visible:outline-hidden focus-visible:bg-muted/40"
    >
      <span className="flex min-w-0 items-baseline gap-3">
        <span className="truncate text-[15px] font-semibold tracking-tight">
          {project.slug}
        </span>
        {project.description && (
          <span className="hidden truncate text-sm text-grey md:inline">
            {project.description}
          </span>
        )}
      </span>

      <span className="flex flex-none items-center gap-5">
        {shownEnvs.length > 0 && (
          <span className="hidden items-center gap-1 lg:flex">
            {shownEnvs.map((env) => (
              <span
                key={env.id}
                className="bg-muted px-1.5 py-0.5 text-[11px] font-medium text-muted-foreground"
              >
                {env.name}
              </span>
            ))}
            {overflow > 0 && (
              <span className="bg-muted px-1.5 py-0.5 text-[11px] font-medium tabular-nums text-muted-foreground">
                +{overflow}
              </span>
            )}
          </span>
        )}

        <span className="flex w-36 items-center gap-2 text-[13px]">
          <Ping color={color} static={color === "green" || color === "gray"} />
          <span className="tabular-nums text-grey">
            {healthy}/{total} healthy
          </span>
        </span>

        <span className="hidden w-16 text-right font-mono text-xs tabular-nums text-grey sm:block">
          {timeAgo(project.updated_at)}
        </span>

        <span className="flex items-center gap-1">
          <button
            type="button"
            onClick={(event) => {
              event.preventDefault();
              event.stopPropagation();
              navigate(`/project/${project.slug}/settings`);
            }}
            className="flex size-7 flex-none items-center justify-center text-grey opacity-0 transition-opacity duration-150 hover:bg-foreground/[0.06] hover:text-foreground group-hover:opacity-100 focus-visible:opacity-100"
            aria-label="Project settings"
          >
            <SettingsIcon size={15} strokeWidth={1.75} />
          </button>
          <ChevronRightIcon
            size={16}
            strokeWidth={1.75}
            className="text-grey/60 transition-transform duration-150 group-hover:translate-x-0.5"
          />
        </span>
      </span>
    </Link>
  );
}

export function ProjectGridCard({ project }: { project: Project }) {
  const healthy =
    (project.healthy_services ?? 0) + (project.healthy_stack_services ?? 0);
  const total =
    (project.total_services ?? 0) + (project.total_stack_services ?? 0);

  let color: StatusBadgeColor = "gray";
  if (total > 0) {
    color = healthy === total ? "green" : healthy === 0 ? "red" : "yellow";
  }

  const envs = project.environments ?? [];

  return (
    <Link
      to={`/project/${project.slug}/production`}
      className="group flex flex-col gap-3 border border-border bg-card p-5 transition-colors duration-150 hover:border-foreground/25 focus-visible:outline-hidden focus-visible:border-foreground/40"
    >
      <span className="flex items-baseline justify-between gap-3">
        <span className="truncate text-[15px] font-semibold tracking-tight">
          {project.slug}
        </span>
        <span className="flex flex-none items-center gap-2 text-[13px]">
          <Ping color={color} static={color === "green" || color === "gray"} />
          <span className="tabular-nums text-grey">
            {healthy}/{total}
          </span>
        </span>
      </span>
      {project.description && (
        <span className="line-clamp-2 text-sm text-grey">
          {project.description}
        </span>
      )}
      <span className="mt-auto flex items-center justify-between gap-3 border-t border-border pt-3">
        <span className="flex min-w-0 items-center gap-1">
          {envs.slice(0, 3).map((env) => (
            <span
              key={env.id}
              className="bg-muted px-1.5 py-0.5 text-[11px] font-medium text-muted-foreground"
            >
              {env.name}
            </span>
          ))}
          {envs.length > 3 && (
            <span className="bg-muted px-1.5 py-0.5 text-[11px] font-medium tabular-nums text-muted-foreground">
              +{envs.length - 3}
            </span>
          )}
        </span>
        <span className="flex-none font-mono text-xs tabular-nums text-grey">
          {timeAgo(project.updated_at)}
        </span>
      </span>
    </Link>
  );
}
