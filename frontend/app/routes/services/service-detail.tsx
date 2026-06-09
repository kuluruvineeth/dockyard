import { useQuery } from "@tanstack/react-query";
import {
  ArrowLeftIcon,
  ExternalLinkIcon,
  InfoIcon,
  LoaderIcon,
  PackageIcon,
  RocketIcon
} from "lucide-react";
import { Fragment, type ReactNode } from "react";
import { Form, Link, useNavigation } from "react-router";
import { apiClient } from "~/api/client";
import { DockerDeploymentCard } from "~/components/deployment-cards";
import { StatusBadge, type StatusBadgeColor } from "~/components/status-badge";
import { SubmitButton } from "~/components/ui/button";
import { Card } from "~/components/ui/card";
import {
  FieldSet,
  FieldSetCheckbox,
  FieldSetInput,
  FieldSetLabel
} from "~/components/ui/fieldset";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger
} from "~/components/ui/tooltip";
import { serviceQueries } from "~/lib/queries";
import { getFormErrorsFromResponseData } from "~/lib/utils";
import { queryClient } from "~/root";
import { getCsrfTokenHeader, metaTitle } from "~/utils";
import type { Route } from "./+types/service-detail";

export const meta: Route.MetaFunction = ({ params }) => [
  metaTitle(params.slug)
];

export async function clientLoader({ params }: Route.ClientLoaderArgs) {
  await queryClient.ensureQueryData(
    serviceQueries.single(params.projectSlug, params.envSlug, params.slug)
  );
  return null;
}

export async function clientAction({
  request,
  params
}: Route.ClientActionArgs) {
  const path = {
    project_slug: params.projectSlug,
    env_slug: params.envSlug,
    slug: params.slug
  };
  const serviceKey = serviceQueries.single(
    params.projectSlug,
    params.envSlug,
    params.slug
  ).queryKey;

  const formData = await request.formData();
  const deploymentsKey = serviceQueries.deployments(
    params.projectSlug,
    params.envSlug,
    params.slug
  ).queryKey;

  const changeField = formData.get("change_field")?.toString();

  if (changeField) {
    let newValue: unknown;
    if (changeField === "env_variables") {
      newValue = {
        key: formData.get("key")?.toString(),
        value: formData.get("value")?.toString() ?? ""
      };
    } else if (changeField === "source") {
      newValue = { image: formData.get("image")?.toString() };
    } else if (changeField === "command") {
      const command = formData.get("command")?.toString()?.trim();
      newValue = command ? command : null;
    } else if (changeField === "ports") {
      newValue = {
        host: Number(formData.get("host")),
        forwarded: Number(formData.get("forwarded"))
      };
    } else if (changeField === "healthcheck") {
      const port = formData.get("associated_port")?.toString();
      newValue = {
        type: formData.get("type")?.toString(),
        value: formData.get("value")?.toString(),
        timeout_seconds: Number(formData.get("timeout_seconds")) || 60,
        interval_seconds: Number(formData.get("interval_seconds")) || 15,
        associated_port: port ? Number(port) : undefined
      };
    } else {
      const urlValue: Record<string, unknown> = {
        domain: formData.get("domain")?.toString(),
        base_path: formData.get("base_path")?.toString() || "/",
        strip_prefix: formData.get("strip_prefix") === "on"
      };
      const port = formData.get("associated_port")?.toString();
      if (port) {
        urlValue.associated_port = Number(port);
      }
      newValue = urlValue;
    }

    const { error } = await apiClient.PUT(
      "/api/projects/{project_slug}/{env_slug}/request-service-changes/{slug}/",
      {
        headers: { ...(await getCsrfTokenHeader()) },
        params: { path },
        body: {
          field: changeField,
          type: formData.get("change_type")?.toString() ?? "ADD",
          new_value: newValue
        }
      }
    );
    if (error) {
      return { changeError: error };
    }
    await queryClient.invalidateQueries({ queryKey: serviceKey });
    return { changeOk: true };
  }

  const { error, data } = await apiClient.PUT(
    "/api/projects/{project_slug}/{env_slug}/deploy-service/docker/{slug}/",
    { headers: { ...(await getCsrfTokenHeader()) }, params: { path } }
  );
  if (error) {
    return { error };
  }
  await queryClient.invalidateQueries({ queryKey: serviceKey });
  await queryClient.invalidateQueries({ queryKey: deploymentsKey });
  return { deployment: data };
}

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

function statusFor(status?: string): {
  color: StatusBadgeColor;
  label: string;
} {
  if (!status) return { color: "gray", label: "No deployment" };
  return STATUS_DISPLAY[status] ?? { color: "gray", label: status };
}

const SECTION_FOOTER =
  "flex flex-col gap-4 border-t border-border/60 bg-muted/25 px-5 py-5";

const DOT_BG: Record<StatusBadgeColor, string> = {
  green: "bg-green-600",
  red: "bg-red-600",
  yellow: "bg-yellow-600",
  blue: "bg-blue-600",
  gray: "bg-gray-500"
};

function timeAgo(iso?: string | null): string {
  if (!iso) return "never";
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return "never";
  const secs = Math.max(0, Math.floor((Date.now() - then) / 1000));
  if (secs < 60) return `${secs}s ago`;
  const mins = Math.floor(secs / 60);
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  if (days < 30) return `${days}d ago`;
  const months = Math.floor(days / 30);
  if (months < 12) return `${months}mo ago`;
  return `${Math.floor(months / 12)}y ago`;
}

function dayLabel(iso?: string | null): string {
  if (!iso) return "Unknown";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "Unknown";
  const now = new Date();
  const startOfDay = (x: Date) =>
    new Date(x.getFullYear(), x.getMonth(), x.getDate()).getTime();
  const diffDays = Math.round((startOfDay(now) - startOfDay(d)) / 86_400_000);
  if (diffDays <= 0) return "Today";
  if (diffDays === 1) return "Yesterday";
  return d.toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: d.getFullYear() === now.getFullYear() ? undefined : "numeric"
  });
}

function SectionCard({
  title,
  description,
  action,
  children
}: {
  title: string;
  description?: string;
  action?: ReactNode;
  children: ReactNode;
}) {
  return (
    <Card className="overflow-hidden transition-colors duration-150 focus-within:border-foreground/25">
      <div className="flex items-start justify-between gap-3 border-b border-border/60 px-5 py-4">
        <div className="min-w-0">
          <h2 className="text-sm font-semibold tracking-tight text-foreground">
            {title}
          </h2>
          {description && (
            <p className="mt-1 text-[13px] leading-relaxed text-grey">
              {description}
            </p>
          )}
        </div>
        {action && <div className="flex-none">{action}</div>}
      </div>
      {children}
    </Card>
  );
}

function InfoRow({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-3 px-5 py-3 text-sm transition-colors duration-150 hover:bg-muted/40">
      <span className="flex-none text-grey">{label}</span>
      <span className="min-w-0 truncate text-right font-mono">{value}</span>
    </div>
  );
}

function EmptyState({ children }: { children: ReactNode }) {
  return <p className="px-5 py-8 text-center text-sm text-grey">{children}</p>;
}

function PendingRow({ children }: { children: ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-3 border-l-2 border-amber-500/60 bg-amber-500/[0.07] px-5 py-3 text-sm">
      <div className="min-w-0 font-mono">{children}</div>
      <StatusBadge color="yellow" pingState="hidden" className="flex-none">
        pending
      </StatusBadge>
    </div>
  );
}

function ServiceDetailSkeleton() {
  return (
    <section className="mx-auto flex w-full max-w-6xl animate-pulse flex-col gap-8">
      <div className="flex flex-col gap-3">
        <div className="h-3 w-40 bg-muted" />
        <div className="flex flex-col gap-2.5">
          <div className="flex items-center gap-2.5">
            <div className="h-8 w-52 bg-muted" />
            <div className="h-5 w-14 bg-muted" />
          </div>
          <div className="h-4 w-72 bg-muted" />
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1fr_320px]">
        <div className="order-last flex flex-col gap-6 lg:order-first">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="border border-border bg-card">
              <div className="flex flex-col gap-2 border-b border-border/60 px-5 py-4">
                <div className="h-4 w-36 bg-muted" />
                <div className="h-3 w-64 bg-muted" />
              </div>
              <div className="flex flex-col gap-3 px-5 py-5">
                <div className="h-4 w-full bg-muted" />
                <div className="h-4 w-2/3 bg-muted" />
              </div>
            </div>
          ))}
        </div>

        <aside className="order-first flex flex-col gap-4 lg:order-last">
          <div className="flex flex-col gap-4 border border-border bg-card p-5">
            <div className="flex items-center justify-between gap-3">
              <div className="h-6 w-24 bg-muted" />
              <div className="h-4 w-12 bg-muted" />
            </div>
            <div className="h-4 w-40 bg-muted" />
            <div className="h-9 w-full bg-muted" />
            <div className="h-9 w-full bg-muted" />
          </div>
          <div className="border border-border bg-card">
            <div className="border-b border-border/60 px-5 py-4">
              <div className="h-4 w-28 bg-muted" />
            </div>
            <div className="divide-y divide-border/60">
              {Array.from({ length: 3 }).map((_, i) => (
                <div
                  key={i}
                  className="flex items-center justify-between gap-3 px-5 py-3"
                >
                  <div className="h-3 w-24 bg-muted" />
                  <div className="h-3 w-12 bg-muted" />
                </div>
              ))}
            </div>
          </div>
        </aside>
      </div>
    </section>
  );
}

export default function ServiceDetail({
  params,
  actionData
}: Route.ComponentProps) {
  const navigation = useNavigation();
  const isPending = navigation.state !== "idle";
  const { data: service } = useQuery(
    serviceQueries.single(params.projectSlug, params.envSlug, params.slug)
  );
  const { data: deployments } = useQuery(
    serviceQueries.deployments(params.projectSlug, params.envSlug, params.slug)
  );

  if (!service) return <ServiceDetailSkeleton />;

  const sourceChange = service?.unapplied_changes.find(
    (c) => c.field === "source"
  );
  const stagedImage = (
    sourceChange?.new_value as { image?: string } | undefined
  )?.image;
  const sourceImage = service?.image ?? stagedImage ?? "";
  const changeErrors = getFormErrorsFromResponseData(
    actionData && "changeError" in actionData
      ? actionData.changeError
      : undefined
  );

  const productionDeployment = deployments?.find(
    (d) => d.is_current_production
  );
  const headerStatus = productionDeployment
    ? statusFor(productionDeployment.status)
    : null;

  const deployment =
    actionData && "deployment" in actionData ? actionData.deployment : null;
  const deployErrors =
    actionData && "error" in actionData ? actionData.error : null;

  const SourceIcon = PackageIcon;
  const sourceText = sourceImage || "—";

  const appliedUrls = service?.urls ?? [];
  const pendingUrls = (service?.unapplied_changes ?? []).filter(
    (c) => c.field === "urls" && c.type === "ADD"
  );
  const appliedEnv = service?.env_variables ?? [];
  const pendingEnv = (service?.unapplied_changes ?? []).filter(
    (c) => c.field === "env_variables" && c.type === "ADD"
  );
  const appliedPorts = service?.ports ?? [];
  const pendingPorts = (service?.unapplied_changes ?? []).filter(
    (c) => c.field === "ports" && c.type === "ADD"
  );
  const pendingCount = service?.unapplied_changes.length ?? 0;
  const lastDeploy = deployments?.[0];
  const recentDeployments = deployments?.slice(0, 3) ?? [];

  return (
    <section className="mx-auto flex w-full max-w-6xl flex-col gap-8">
      <div className="flex flex-col gap-3">
        <Link
          to={`/project/${params.projectSlug}/${params.envSlug}`}
          className="inline-flex w-fit items-center gap-1.5 text-[11px] font-medium uppercase tracking-[0.18em] text-grey transition-colors duration-150 hover:text-foreground"
        >
          <ArrowLeftIcon size={12} strokeWidth={2} /> {params.projectSlug} /{" "}
          {params.envSlug}
        </Link>
        <div className="flex min-w-0 flex-col gap-2.5">
          <div className="flex flex-wrap items-center gap-2.5">
            <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">
              {params.slug}
            </h1>
          </div>
          <div className="flex min-w-0 items-center gap-1.5 font-mono text-[13px] text-grey">
            <SourceIcon size={13} strokeWidth={1.75} className="flex-none" />
            <span className="truncate">{sourceText}</span>
          </div>
        </div>
      </div>

      {deployErrors && (
        <div className="border border-destructive/40 bg-destructive/5 p-4 text-sm text-destructive">
          Deploy failed: {deployErrors.errors.map((e) => e.detail).join(" ")}
        </div>
      )}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1fr_320px]">
        <div
          id="config"
          className="order-last flex scroll-mt-20 flex-col gap-6 lg:order-first"
        >
          <SectionCard
            title="Source"
            description="The image this service runs and its internal network alias."
          >
            <div className="divide-y divide-border/60">
              <InfoRow
                label="Network alias"
                value={service?.network_alias ?? "—"}
              />
            </div>
            <Form method="POST" className={SECTION_FOOTER}>
              <input type="hidden" name="change_field" value="source" />
              <input type="hidden" name="change_type" value="UPDATE" />
              {changeErrors.new_value && (
                <p className="text-sm text-destructive">
                  {changeErrors.new_value.join(" ")}
                </p>
              )}
              <FieldSet required className="flex flex-col gap-1.5">
                <FieldSetLabel>Image</FieldSetLabel>
                <FieldSetInput
                  name="image"
                  className="font-mono"
                  placeholder="ex: redis:alpine"
                  defaultValue={sourceImage}
                  required
                />
              </FieldSet>
              <SubmitButton
                isPending={isPending}
                variant="outline"
                className="w-fit"
              >
                {isPending ? "Saving…" : "Update image"}
              </SubmitButton>
            </Form>
          </SectionCard>

          <SectionCard
            title="Startup command"
            description="Overrides the default command run inside the container."
          >
            <Form method="POST" className="flex flex-col gap-4 px-5 py-5">
              <input type="hidden" name="change_field" value="command" />
              <input type="hidden" name="change_type" value="UPDATE" />
              <FieldSet className="flex flex-col gap-1.5">
                <FieldSetLabel>Custom command (optional)</FieldSetLabel>
                <FieldSetInput
                  name="command"
                  className="font-mono"
                  placeholder="ex: npm run start"
                  defaultValue={service?.command ?? ""}
                />
              </FieldSet>
              <SubmitButton
                isPending={isPending}
                variant="outline"
                className="w-fit"
              >
                {isPending ? "Saving…" : "Update command"}
              </SubmitButton>
            </Form>
          </SectionCard>

          <SectionCard
            title="URLs"
            description="Domains and base paths routed to this service."
          >
            <div className="divide-y divide-border/60">
              {appliedUrls.length === 0 && pendingUrls.length === 0 && (
                <EmptyState>
                  No URLs yet. Add a domain below to route traffic here.
                </EmptyState>
              )}
              {appliedUrls.map((url) => (
                <div
                  key={url.id}
                  className="flex items-center justify-between gap-3 px-5 py-3 text-sm transition-colors duration-150 hover:bg-muted/40"
                >
                  <a
                    href={`//${url.domain}${url.base_path}`}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex min-w-0 items-center gap-1 font-mono transition-colors duration-150 hover:text-primary"
                  >
                    <span className="truncate">
                      {url.domain}
                      <span className="text-grey">{url.base_path}</span>
                    </span>
                    <ExternalLinkIcon
                      size={13}
                      className="flex-none text-grey"
                    />
                  </a>
                  {url.associated_port && (
                    <span className="flex-none font-mono text-sm tabular-nums text-grey">
                      :{url.associated_port}
                    </span>
                  )}
                </div>
              ))}
              {pendingUrls.map((change) => {
                const value = change.new_value as {
                  domain?: string;
                  base_path?: string;
                };
                return (
                  <PendingRow key={change.id}>
                    {value.domain}
                    <span className="text-grey">{value.base_path}</span>
                  </PendingRow>
                );
              })}
            </div>
            <NewServiceURLForm actionData={actionData} isPending={isPending} />
          </SectionCard>

          <SectionCard
            title="Exposed ports"
            description="Map a host port to a container port. Use URLs for HTTP traffic."
          >
            <div className="divide-y divide-border/60">
              {appliedPorts.length === 0 && pendingPorts.length === 0 && (
                <EmptyState>No exposed ports yet.</EmptyState>
              )}
              {appliedPorts.map((port) => (
                <div
                  key={port.id}
                  className="flex items-center gap-2 px-5 py-3 font-mono text-sm tabular-nums transition-colors duration-150 hover:bg-muted/40"
                >
                  <span>{port.host}</span>
                  <span className="text-grey">→</span>
                  <span className="text-grey">{port.forwarded}</span>
                </div>
              ))}
              {pendingPorts.map((change) => {
                const value = change.new_value as {
                  host?: number;
                  forwarded?: number;
                };
                return (
                  <PendingRow key={change.id}>
                    <span className="tabular-nums">{value.host}</span>{" "}
                    <span className="text-grey">→</span>{" "}
                    <span className="tabular-nums">{value.forwarded}</span>
                  </PendingRow>
                );
              })}
            </div>
            <NewServicePortForm actionData={actionData} isPending={isPending} />
          </SectionCard>

          <SectionCard
            title="Environment variables"
            description="Injected into the service at deploy time."
          >
            <div className="divide-y divide-border/60">
              {appliedEnv.length === 0 && pendingEnv.length === 0 && (
                <EmptyState>
                  No variables yet. Add a key and value below.
                </EmptyState>
              )}
              {appliedEnv.map((env) => (
                <div
                  key={env.id}
                  className="flex items-center gap-2 px-5 py-3 font-mono text-sm transition-colors duration-150 hover:bg-muted/40"
                >
                  <span className="flex-none">{env.key}</span>
                  <span className="text-grey">=</span>
                  <span className="truncate text-grey">{env.value}</span>
                </div>
              ))}
              {pendingEnv.map((change) => {
                const value = change.new_value as {
                  key?: string;
                  value?: string;
                };
                return (
                  <PendingRow key={change.id}>
                    {value.key} <span className="text-grey">=</span>{" "}
                    <span className="text-grey">{value.value}</span>
                  </PendingRow>
                );
              })}
            </div>
            <NewEnvVariableForm actionData={actionData} isPending={isPending} />
          </SectionCard>

          <SectionCard
            title="Healthcheck"
            description="Determines when a deployment is considered healthy."
          >
            <Form method="POST" className="flex flex-col gap-4 px-5 py-5">
              <input type="hidden" name="change_field" value="healthcheck" />
              <input type="hidden" name="change_type" value="UPDATE" />

              {changeErrors.new_value && (
                <p className="text-sm text-destructive">
                  {changeErrors.new_value.join(" ")}
                </p>
              )}

              <div className="flex flex-col gap-4 md:flex-row">
                <FieldSet className="inline-flex flex-col gap-1.5">
                  <FieldSetLabel>Type</FieldSetLabel>
                  <select
                    name="type"
                    defaultValue={service?.healthcheck?.type ?? "PATH"}
                    className="h-10 border border-border bg-background px-3 text-sm transition-colors duration-150 hover:border-foreground/15 focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-ring/70"
                  >
                    <option value="PATH">Path</option>
                    <option value="COMMAND">Command</option>
                  </select>
                </FieldSet>
                <FieldSet
                  required
                  className="inline-flex flex-1 flex-col gap-1.5"
                >
                  <FieldSetLabel>Value</FieldSetLabel>
                  <FieldSetInput
                    name="value"
                    className="font-mono"
                    placeholder="ex: /health"
                    defaultValue={service?.healthcheck?.value ?? ""}
                    required
                  />
                </FieldSet>
              </div>

              <div className="flex flex-col gap-4 md:flex-row">
                <FieldSet className="inline-flex flex-1 flex-col gap-1.5">
                  <FieldSetLabel>
                    Forwarded port (for path checks)
                  </FieldSetLabel>
                  <FieldSetInput
                    name="associated_port"
                    className="font-mono"
                    placeholder="ex: 8080"
                    defaultValue={service?.healthcheck?.associated_port ?? ""}
                  />
                </FieldSet>
                <FieldSet className="inline-flex flex-col gap-1.5">
                  <FieldSetLabel>Timeout (s)</FieldSetLabel>
                  <FieldSetInput
                    name="timeout_seconds"
                    className="font-mono"
                    defaultValue={service?.healthcheck?.timeout_seconds ?? 60}
                  />
                </FieldSet>
                <FieldSet className="inline-flex flex-col gap-1.5">
                  <FieldSetLabel>Interval (s)</FieldSetLabel>
                  <FieldSetInput
                    name="interval_seconds"
                    className="font-mono"
                    defaultValue={service?.healthcheck?.interval_seconds ?? 15}
                  />
                </FieldSet>
              </div>

              <SubmitButton
                isPending={isPending}
                variant="outline"
                className="w-fit"
              >
                {isPending ? "Saving…" : "Save healthcheck"}
              </SubmitButton>
            </Form>
          </SectionCard>
        </div>

        <aside className="order-first flex flex-col gap-4 lg:order-last lg:sticky lg:top-20 lg:self-start">
          <Card className="flex flex-col gap-4 p-5">
            <div className="flex items-center justify-between gap-3">
              <StatusBadge
                color={headerStatus?.color ?? "gray"}
                className="px-3 py-1 text-[13px]"
              >
                {headerStatus?.label ?? "No deployment"}
              </StatusBadge>
              <span className="font-mono text-xs tabular-nums text-grey">
                {lastDeploy ? timeAgo(lastDeploy.queued_at) : ""}
              </span>
            </div>
            <div className="flex min-w-0 items-center gap-1.5 font-mono text-[13px] text-grey">
              <SourceIcon size={13} strokeWidth={1.75} className="flex-none" />
              <span className="truncate">{sourceText}</span>
            </div>
            {appliedUrls.length > 0 && (
              <a
                href={`//${appliedUrls[0].domain}${appliedUrls[0].base_path}`}
                target="_blank"
                rel="noreferrer"
                className="inline-flex min-w-0 items-center gap-1.5 font-mono text-[13px] text-foreground transition-colors duration-150 hover:text-primary focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-ring/70"
              >
                <span className="truncate">
                  {appliedUrls[0].domain}
                  <span className="text-grey">{appliedUrls[0].base_path}</span>
                </span>
                <ExternalLinkIcon size={13} className="flex-none text-grey" />
              </a>
            )}
            <Form method="POST">
              <SubmitButton isPending={isPending} className="w-full gap-1.5">
                {isPending ? (
                  <>
                    <span>Deploying…</span>
                    <LoaderIcon className="animate-spin" size={15} />
                  </>
                ) : (
                  <>
                    <RocketIcon size={15} strokeWidth={1.75} /> Deploy
                  </>
                )}
              </SubmitButton>
            </Form>
            {pendingCount > 0 && (
              <a
                href="#config"
                className="flex items-center justify-between gap-2 border-l-2 border-amber-500/60 bg-amber-500/[0.07] px-3 py-2 text-[13px] text-amber-700 transition-colors duration-150 hover:bg-amber-500/[0.12] dark:text-amber-500"
              >
                <span className="tabular-nums">
                  {pendingCount} pending change{pendingCount > 1 ? "s" : ""}
                </span>
                <span className="text-xs text-grey">review</span>
              </a>
            )}
            {deployment && (
              <p className="truncate font-mono text-xs text-grey">
                Triggered {deployment.slot.toLowerCase()} slot · {deployment.id}
              </p>
            )}
          </Card>

          {deployments && deployments.length > 0 && (
            <SectionCard
              title="Deployments"
              action={
                deployments.length > 3 ? (
                  <a
                    href="#deployments"
                    className="text-xs font-medium text-grey transition-colors duration-150 hover:text-foreground"
                  >
                    View all
                  </a>
                ) : undefined
              }
            >
              <div className="divide-y divide-border/60">
                {recentDeployments.map((dpl) => {
                  const hash = dpl.id.split("_").pop() ?? "";
                  const color = statusFor(dpl.status).color;
                  return (
                    <div
                      key={dpl.id}
                      className="flex items-center justify-between gap-3 px-5 py-3"
                    >
                      <div className="flex min-w-0 items-center gap-2">
                        <span
                          className={`size-2 flex-none rounded-full ${DOT_BG[color]}`}
                        />
                        <span className="truncate font-mono text-xs">
                          {hash}
                        </span>
                      </div>
                      <span className="flex-none font-mono text-xs tabular-nums text-grey">
                        {timeAgo(dpl.queued_at)}
                      </span>
                    </div>
                  );
                })}
              </div>
            </SectionCard>
          )}
        </aside>
      </div>

      {deployments && deployments.length > 0 && (
        <div id="deployments" className="flex scroll-mt-20 flex-col gap-5">
          <div className="flex items-baseline justify-between">
            <h2 className="text-xs font-medium uppercase tracking-[0.16em] text-grey">
              Deployment history
            </h2>
            <span className="font-mono text-xs tabular-nums text-grey">
              {deployments.length}
            </span>
          </div>
          <ol className="relative flex flex-col gap-3 before:absolute before:bottom-3 before:left-[7px] before:top-3 before:w-px before:bg-border before:content-['']">
            {deployments.map((dpl, i) => {
              const color = statusFor(dpl.status).color;
              const label = dayLabel(dpl.queued_at);
              const showHeader =
                i === 0 || label !== dayLabel(deployments[i - 1].queued_at);
              return (
                <Fragment key={dpl.id}>
                  {showHeader && (
                    <li className="relative z-10 pl-8 pt-3 first:pt-0">
                      <span className="bg-background pr-2 text-[11px] font-medium uppercase tracking-[0.16em] text-grey">
                        {label}
                      </span>
                    </li>
                  )}
                  <li className="relative pl-8">
                    <span
                      className={`absolute left-[3px] top-6 size-2 rounded-full ring-4 ring-background ${DOT_BG[color]}`}
                    />
                    <DockerDeploymentCard deployment={dpl} />
                  </li>
                </Fragment>
              );
            })}
          </ol>
        </div>
      )}
    </section>
  );
}

function NewServicePortForm({
  actionData,
  isPending
}: {
  actionData: Route.ComponentProps["actionData"];
  isPending: boolean;
}) {
  const errors = getFormErrorsFromResponseData(
    actionData && "changeError" in actionData
      ? actionData.changeError
      : undefined
  );

  return (
    <Form method="POST" className={SECTION_FOOTER}>
      <input type="hidden" name="change_field" value="ports" />
      <input type="hidden" name="change_type" value="ADD" />

      {errors.new_value && (
        <p className="text-sm text-destructive">{errors.new_value.join(" ")}</p>
      )}

      <div className="flex flex-col gap-4 md:flex-row md:items-end">
        <FieldSet required className="inline-flex flex-1 flex-col gap-1.5">
          <FieldSetLabel>Forwarded port</FieldSetLabel>
          <FieldSetInput
            name="forwarded"
            placeholder="ex: 8080"
            className="font-mono"
            required
          />
        </FieldSet>
        <FieldSet required className="inline-flex flex-1 flex-col gap-1.5">
          <FieldSetLabel>Host port</FieldSetLabel>
          <FieldSetInput
            name="host"
            placeholder="ex: 8080"
            className="font-mono"
            required
          />
        </FieldSet>
        <SubmitButton isPending={isPending} variant="outline" className="w-fit">
          {isPending ? "Adding…" : "Add"}
        </SubmitButton>
      </div>
    </Form>
  );
}

function NewEnvVariableForm({
  actionData,
  isPending
}: {
  actionData: Route.ComponentProps["actionData"];
  isPending: boolean;
}) {
  const errors = getFormErrorsFromResponseData(
    actionData && "changeError" in actionData
      ? actionData.changeError
      : undefined
  );

  return (
    <Form method="POST" className={SECTION_FOOTER}>
      <input type="hidden" name="change_field" value="env_variables" />
      <input type="hidden" name="change_type" value="ADD" />

      {errors.new_value && (
        <p className="text-sm text-destructive">{errors.new_value.join(" ")}</p>
      )}

      <div className="flex flex-col gap-4 md:flex-row md:items-end">
        <FieldSet required className="inline-flex flex-1 flex-col gap-1.5">
          <FieldSetLabel>Name</FieldSetLabel>
          <FieldSetInput
            name="key"
            placeholder="VARIABLE_NAME"
            className="font-mono"
            required
          />
        </FieldSet>
        <FieldSet className="inline-flex flex-1 flex-col gap-1.5">
          <FieldSetLabel>Value</FieldSetLabel>
          <FieldSetInput
            name="value"
            placeholder="value"
            className="font-mono"
          />
        </FieldSet>
        <SubmitButton isPending={isPending} variant="outline" className="w-fit">
          {isPending ? "Adding…" : "Add"}
        </SubmitButton>
      </div>
    </Form>
  );
}

function NewServiceURLForm({
  actionData,
  isPending
}: {
  actionData: Route.ComponentProps["actionData"];
  isPending: boolean;
}) {
  const errors = getFormErrorsFromResponseData(
    actionData && "changeError" in actionData
      ? actionData.changeError
      : undefined
  );

  return (
    <Form method="POST" className={SECTION_FOOTER}>
      <input type="hidden" name="change_field" value="urls" />
      <input type="hidden" name="change_type" value="ADD" />

      {errors.new_value && (
        <p className="text-sm text-destructive">{errors.new_value.join(" ")}</p>
      )}

      <FieldSet required className="inline-flex flex-1 flex-col gap-1.5">
        <FieldSetLabel>Forwarded port</FieldSetLabel>
        <FieldSetInput
          placeholder="ex: 3000"
          name="associated_port"
          className="font-mono"
          defaultValue={80}
        />
      </FieldSet>

      <FieldSet required className="inline-flex flex-1 flex-col gap-1.5">
        <FieldSetLabel>Domain</FieldSetLabel>
        <FieldSetInput
          name="domain"
          className="font-mono"
          placeholder="ex: www.mysupersaas.co"
          required
        />
      </FieldSet>

      <FieldSet required className="inline-flex flex-1 flex-col gap-1.5">
        <FieldSetLabel>Base path</FieldSetLabel>
        <FieldSetInput
          name="base_path"
          className="font-mono"
          placeholder="ex: /api"
          defaultValue="/"
        />
      </FieldSet>

      <FieldSet className="inline-flex flex-1 flex-col gap-2">
        <div className="inline-flex items-center gap-2">
          <FieldSetCheckbox name="strip_prefix" defaultChecked />
          <FieldSetLabel className="inline-flex items-center gap-1">
            Strip path prefix?
            <TooltipProvider>
              <Tooltip delayDuration={0}>
                <TooltipTrigger type="button">
                  <InfoIcon size={15} />
                </TooltipTrigger>
                <TooltipContent className="max-w-48">
                  Whether to omit the base path when passing the request to your
                  service.
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          </FieldSetLabel>
        </div>
      </FieldSet>

      <SubmitButton isPending={isPending} variant="outline" className="w-fit">
        {isPending ? "Adding…" : "Add URL"}
      </SubmitButton>
    </Form>
  );
}
