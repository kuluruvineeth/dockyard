import { useQuery } from "@tanstack/react-query";
import {
  ArrowLeftIcon,
  LoaderIcon,
  PackageIcon,
  RocketIcon
} from "lucide-react";
import type { ReactNode } from "react";
import { Form, Link, useNavigation } from "react-router";
import { apiClient } from "~/api/client";
import { StatusBadge } from "~/components/status-badge";
import { SubmitButton } from "~/components/ui/button";
import { Card } from "~/components/ui/card";
import { serviceQueries } from "~/lib/queries";
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

export async function clientAction({ params }: Route.ClientActionArgs) {
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

  const { error, data } = await apiClient.PUT(
    "/api/projects/{project_slug}/{env_slug}/deploy-service/docker/{slug}/",
    { headers: { ...(await getCsrfTokenHeader()) }, params: { path } }
  );
  if (error) {
    return { error };
  }
  await queryClient.invalidateQueries({ queryKey: serviceKey });
  return { deployment: data };
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
          {Array.from({ length: 1 }).map((_, i) => (
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

  if (!service) return <ServiceDetailSkeleton />;

  const sourceChange = service?.unapplied_changes.find(
    (c) => c.field === "source"
  );
  const stagedImage = (
    sourceChange?.new_value as { image?: string } | undefined
  )?.image;
  const sourceImage = service?.image ?? stagedImage ?? "";

  const deployment =
    actionData && "deployment" in actionData ? actionData.deployment : null;
  const deployErrors =
    actionData && "error" in actionData ? actionData.error : null;

  const SourceIcon = PackageIcon;
  const sourceText = sourceImage || "—";

  const pendingCount = service?.unapplied_changes.length ?? 0;

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
              <InfoRow label="Image" value={sourceImage || "—"} />
              <InfoRow
                label="Network alias"
                value={service?.network_alias ?? "—"}
              />
            </div>
          </SectionCard>
        </div>

        <aside className="order-first flex flex-col gap-4 lg:order-last lg:sticky lg:top-20 lg:self-start">
          <Card className="flex flex-col gap-4 p-5">
            <div className="flex items-center justify-between gap-3">
              <StatusBadge color="gray" className="px-3 py-1 text-[13px]">
                No deployment
              </StatusBadge>
            </div>
            <div className="flex min-w-0 items-center gap-1.5 font-mono text-[13px] text-grey">
              <SourceIcon size={13} strokeWidth={1.75} className="flex-none" />
              <span className="truncate">{sourceText}</span>
            </div>
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
        </aside>
      </div>
    </section>
  );
}
