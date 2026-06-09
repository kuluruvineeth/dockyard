import { useQuery } from "@tanstack/react-query";
import { RotateCcwIcon, ScrollTextIcon } from "lucide-react";
import { type ReactNode, useState } from "react";
import { Form } from "react-router";
import type { ApiResponse } from "~/api/client";
import { StatusBadge, type StatusBadgeColor } from "~/components/status-badge";
import { Button } from "~/components/ui/button";
import { Card } from "~/components/ui/card";
import { serviceQueries } from "~/lib/queries";
import { cn } from "~/lib/utils";

type Deployment = ApiResponse<
  "get",
  "/api/projects/{project_slug}/{env_slug}/service-details/{slug}/deployments/"
>["results"][number];

const STATUS_DISPLAY: Record<
  string,
  { color: StatusBadgeColor; label: string }
> = {
  HEALTHY: { color: "green", label: "Healthy" },
  UNHEALTHY: { color: "red", label: "Unhealthy" },
  FAILED: { color: "red", label: "Failed" },
  STARTING: { color: "blue", label: "Starting" },
  BUILDING: { color: "blue", label: "Building" },
  PREPARING: { color: "blue", label: "Preparing" },
  CANCELLED: { color: "gray", label: "Cancelled" },
  SLEEPING: { color: "gray", label: "Sleeping" },
  QUEUED: { color: "yellow", label: "Queued" },
  REMOVED: { color: "gray", label: "Removed" }
};

function SlotBadge({ slot }: { slot: string }) {
  const isGreen = slot.toUpperCase() === "GREEN";
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2 py-0.5 font-mono text-[11px] font-medium uppercase tracking-[0.12em] ring-1",
        isGreen
          ? "bg-green-500/10 text-green-600 ring-green-500/25 dark:text-green-400"
          : "bg-blue-500/10 text-blue-600 ring-blue-500/25 dark:text-blue-300"
      )}
    >
      {slot.toLowerCase()}
    </span>
  );
}

type Panel = "logs" | null;

function SegButton({
  active,
  onClick,
  children
}: {
  active: boolean;
  onClick: () => void;
  children: ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium transition-colors duration-150",
        active
          ? "bg-card text-foreground shadow-xs"
          : "text-grey hover:text-foreground"
      )}
    >
      {children}
    </button>
  );
}

export function DockerDeploymentCard({
  deployment,
  projectSlug,
  envSlug,
  serviceSlug
}: {
  deployment: Deployment;
  projectSlug: string;
  envSlug: string;
  serviceSlug: string;
}) {
  const hash = deployment.id.split("_").pop() ?? "";
  const display = STATUS_DISPLAY[deployment.status] ?? {
    color: "gray" as StatusBadgeColor,
    label: deployment.status
  };

  const [panel, setPanel] = useState<Panel>(null);
  const showLogs = panel === "logs";

  const { data: logs, isLoading: logsLoading } = useQuery({
    ...serviceQueries.deploymentLogs(projectSlug, envSlug, serviceSlug, hash),
    enabled: showLogs
  });

  return (
    <Card
      className={cn(
        "flex flex-col gap-4 p-5 transition duration-200 ease-spring hover:border-foreground/15 hover:bg-muted/40",
        deployment.is_current_production && "ring-1 ring-foreground/30"
      )}
    >
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex min-w-0 flex-col gap-2">
          <div className="flex flex-wrap items-center gap-2">
            <StatusBadge color={display.color}>{display.label}</StatusBadge>
            <SlotBadge slot={deployment.slot} />
            {deployment.is_current_production && (
              <span className="inline-flex items-center rounded-full bg-foreground/10 px-2 py-0.5 text-[11px] font-medium uppercase tracking-[0.14em] text-foreground ring-1 ring-foreground/20">
                Production
              </span>
            )}
          </div>
          <span className="font-medium tracking-tight">
            {deployment.commit_message}
          </span>
          <div className="flex flex-wrap items-center gap-x-2 gap-y-1 font-mono text-[13px] tabular-nums">
            <span className="text-foreground/80">{hash}</span>
            {deployment.status_reason && (
              <span className="text-grey">· {deployment.status_reason}</span>
            )}
          </div>
        </div>
        <div className="flex flex-none flex-col gap-2.5 sm:items-end">
          <div className="flex flex-col gap-0.5 font-mono text-[12px] tabular-nums text-grey sm:text-right">
            <span>
              queued {new Date(deployment.queued_at).toLocaleString()}
            </span>
            {deployment.finished_at && (
              <span>
                finished {new Date(deployment.finished_at).toLocaleString()}
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            <div className="inline-flex items-center gap-1 bg-muted p-1">
              <SegButton
                active={showLogs}
                onClick={() => setPanel((p) => (p === "logs" ? null : "logs"))}
              >
                <ScrollTextIcon size={14} strokeWidth={1.75} /> Logs
              </SegButton>
            </div>
            <Form method="POST">
              <input type="hidden" name="intent" value="redeploy" />
              <input type="hidden" name="deployment_hash" value={hash} />
              <Button
                type="submit"
                variant="outline"
                size="sm"
                className="gap-1.5"
              >
                <RotateCcwIcon size={15} strokeWidth={1.75} /> Redeploy
              </Button>
            </Form>
          </div>
        </div>
      </div>

      {showLogs && (
        <div className="max-h-72 overflow-auto border border-white/10 bg-[#0a0a0a] font-mono text-xs leading-relaxed tabular-nums">
          <div className="sticky top-0 z-10 flex items-center justify-between border-b border-white/10 bg-[#0a0a0a] px-3 py-2 text-[11px] uppercase tracking-[0.16em]">
            <span className="text-white/40">Logs</span>
            <span className="tabular-nums text-white/30">
              {logsLoading
                ? "…"
                : `${logs?.length ?? 0} ${(logs?.length ?? 0) === 1 ? "line" : "lines"}`}
            </span>
          </div>
          <div className="p-2">
            {logsLoading ? (
              <span className="px-2 text-white/40">Loading logs...</span>
            ) : (logs?.length ?? 0) > 0 ? (
              logs?.map((line, i) => (
                <div
                  key={`${i}-${line}`}
                  className="whitespace-pre-wrap px-2 py-px text-white/70 transition-colors hover:bg-white/[0.05]"
                >
                  {line}
                </div>
              ))
            ) : (
              <span className="px-2 text-white/40">No logs.</span>
            )}
          </div>
        </div>
      )}
    </Card>
  );
}
