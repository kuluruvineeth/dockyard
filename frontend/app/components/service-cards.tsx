import { BoxIcon, GitBranchIcon, HardDriveIcon, LinkIcon } from "lucide-react";
import { Link } from "react-router";
import type { ApiResponse } from "~/api/client";
import { StatusBadge } from "~/components/status-badge";

type ServiceCard = ApiResponse<
  "get",
  "/api/projects/{project_slug}/{env_slug}/service-list/"
>[number];

function formatRelativeTime(iso: string): string {
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return "";
  const diff = Date.now() - then;
  if (diff < 0) return "just now";
  const sec = Math.round(diff / 1000);
  if (sec < 60) return "just now";
  const min = Math.round(sec / 60);
  if (min < 60) return `${min}m ago`;
  const hr = Math.round(min / 60);
  if (hr < 24) return `${hr}h ago`;
  const day = Math.round(hr / 24);
  if (day < 30) return `${day}d ago`;
  const mo = Math.round(day / 30);
  if (mo < 12) return `${mo}mo ago`;
  return `${Math.round(mo / 12)}y ago`;
}

function stripScheme(url: string): string {
  return url.replace(/^https?:\/\//, "").replace(/\/$/, "");
}

export function DockerServiceCard({
  card,
  projectSlug,
  envSlug
}: {
  card: ServiceCard;
  projectSlug: string;
  envSlug: string;
}) {
  const tag = card.tag ? `:${card.tag}` : "";
  const isGit = card.type === "git";
  const TypeIcon = isGit ? GitBranchIcon : BoxIcon;
  const lastDeploy = formatRelativeTime(card.updated_at);
  const source = card.image
    ? `${card.image}${tag}`
    : isGit
      ? "Git repository"
      : "No image";

  return (
    <Link
      to={`/project/${projectSlug}/${envSlug}/services/${card.slug}`}
      className="group ease-spring grid grid-cols-[auto_1fr_auto] items-center gap-4 px-4 py-3.5 transition-colors duration-200 hover:bg-muted/40 focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring/70 md:grid-cols-[auto_1fr_auto_auto_auto]"
    >
      <span className="flex size-9 flex-none items-center justify-center bg-muted text-foreground">
        <TypeIcon size={16} strokeWidth={1.75} />
      </span>

      <div className="flex min-w-0 flex-col gap-0.5">
        <span className="truncate font-medium tracking-tight">{card.slug}</span>
        <span className="truncate font-mono text-[13px] text-muted-foreground">
          {source}
        </span>
      </div>

      {card.url ? (
        <span className="hidden max-w-[220px] items-center gap-1.5 bg-muted px-2 py-1 font-mono text-xs text-muted-foreground md:inline-flex">
          <LinkIcon size={12} strokeWidth={1.75} className="flex-none" />
          <span className="truncate">{stripScheme(card.url)}</span>
        </span>
      ) : (
        <span className="hidden md:block" aria-hidden />
      )}

      <StatusBadge color="gray" pingState="hidden">
        Not deployed yet
      </StatusBadge>

      <span className="hidden items-center gap-3 font-mono text-xs tabular-nums text-muted-foreground lg:flex">
        {card.volume_number > 0 && (
          <span className="inline-flex items-center gap-1">
            <HardDriveIcon size={12} strokeWidth={1.75} />
            {card.volume_number}
          </span>
        )}
        <span>{lastDeploy ? lastDeploy : "not deployed"}</span>
      </span>
    </Link>
  );
}
