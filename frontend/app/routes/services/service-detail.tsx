import { useQuery } from "@tanstack/react-query";
import {
  ArrowLeftIcon,
  ExternalLinkIcon,
  InfoIcon,
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
  return { deployment: data };
}

const SECTION_FOOTER =
  "flex flex-col gap-4 border-t border-border/60 bg-muted/25 px-5 py-5";

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
  const changeErrors = getFormErrorsFromResponseData(
    actionData && "changeError" in actionData
      ? actionData.changeError
      : undefined
  );

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
        </aside>
      </div>
    </section>
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
