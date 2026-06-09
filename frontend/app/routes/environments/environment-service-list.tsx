import { useQuery } from "@tanstack/react-query";
import {
  BoxIcon,
  MoreHorizontalIcon,
  PlusIcon,
  Trash2Icon
} from "lucide-react";
import { Form, Link, redirect } from "react-router";
import { apiClient } from "~/api/client";
import { DockerServiceCard } from "~/components/service-cards";
import { Button } from "~/components/ui/button";
import { Card } from "~/components/ui/card";
import { FieldSetInput } from "~/components/ui/fieldset";
import {
  Popover,
  PopoverContent,
  PopoverTrigger
} from "~/components/ui/popover";
import { environmentQueries, projectQueries } from "~/lib/queries";
import { cn } from "~/lib/utils";
import { queryClient } from "~/root";
import { getCsrfTokenHeader, metaTitle } from "~/utils";
import type { Route } from "./+types/environment-service-list";

export const meta: Route.MetaFunction = ({ params }) => [
  metaTitle(`${params.projectSlug} / ${params.envSlug}`)
];

export async function clientLoader({ params }: Route.ClientLoaderArgs) {
  await Promise.all([
    queryClient.ensureQueryData(
      environmentQueries.serviceList(params.projectSlug, params.envSlug)
    ),
    queryClient.ensureQueryData(projectQueries.single(params.projectSlug))
  ]);
  return null;
}

export async function clientAction({
  request,
  params
}: Route.ClientActionArgs) {
  const formData = await request.formData();
  const projectKey = projectQueries.single(params.projectSlug).queryKey;

  if (formData.get("intent")?.toString() === "delete-env") {
    const { error } = await apiClient.DELETE(
      "/api/projects/{project_slug}/environments/{env_slug}/",
      {
        headers: { ...(await getCsrfTokenHeader()) },
        params: {
          path: {
            project_slug: params.projectSlug,
            env_slug: formData.get("env_name")?.toString() ?? ""
          }
        }
      }
    );
    if (error) {
      return { error };
    }
    await queryClient.invalidateQueries({ queryKey: projectKey });
    throw redirect(`/project/${params.projectSlug}/production`);
  }

  const { error, data } = await apiClient.POST(
    "/api/projects/{project_slug}/environments/",
    {
      headers: { ...(await getCsrfTokenHeader()) },
      params: { path: { project_slug: params.projectSlug } },
      body: { name: formData.get("name")?.toString() ?? "" }
    }
  );
  if (error) {
    return { error };
  }
  await queryClient.invalidateQueries({ queryKey: projectKey });
  throw redirect(`/project/${params.projectSlug}/${data.name}`);
}

function EnvironmentServiceListSkeleton() {
  return (
    <section className="flex animate-pulse flex-col gap-8">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex flex-col gap-2.5">
          <div className="h-8 w-48 bg-muted" />
          <div className="h-4 w-72 bg-muted" />
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <div className="h-9 w-44 bg-muted" />
        </div>
      </div>

      <div className="-mt-2 flex flex-wrap divide-x divide-border border-y border-border">
        {Array.from({ length: 2 }).map((_, i) => (
          <div key={i} className="flex flex-col gap-1.5 px-6 py-3 first:pl-0">
            <div className="h-7 w-8 bg-muted" />
            <div className="h-3 w-16 bg-muted" />
          </div>
        ))}
      </div>

      <div className="flex items-center gap-2">
        <div className="h-9 w-40 bg-muted" />
        <div className="size-8 bg-muted" />
      </div>

      <div className="flex flex-col gap-3">
        <div className="h-3 w-24 bg-muted" />
        <div className="divide-y divide-border overflow-hidden border border-border bg-card">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="flex items-center gap-4 px-4 py-4">
              <div className="size-9 flex-none bg-muted" />
              <div className="flex flex-1 flex-col gap-2">
                <div className="h-4 w-40 bg-muted" />
                <div className="h-3 w-56 bg-muted" />
              </div>
              <div className="h-5 w-16 bg-muted" />
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

export default function EnvironmentServiceList({
  params,
  actionData
}: Route.ComponentProps) {
  const { projectSlug, envSlug } = params;
  const { data: services } = useQuery(
    environmentQueries.serviceList(projectSlug, envSlug)
  );
  const { data: project } = useQuery(projectQueries.single(projectSlug));

  if (!services || !project) return <EnvironmentServiceListSkeleton />;

  const environments = project.environments ?? [];
  const deletableEnvs = environments.filter((env) => env.name !== "production");

  const serviceCount = services?.length ?? 0;
  const healthyCount =
    services?.filter((s) => s.status === "HEALTHY").length ?? 0;
  const allHealthy = serviceCount > 0 && healthyCount === serviceCount;
  const stats = [
    { label: "Services", value: serviceCount, healthy: false },
    { label: "Healthy", value: healthyCount, healthy: true }
  ];

  return (
    <section className="flex flex-col gap-8">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex flex-col gap-1.5">
          <h1 className="text-2xl font-bold tracking-tighter sm:text-3xl">
            {projectSlug}
          </h1>
          <p className="text-sm text-muted-foreground">
            Services running in{""}
            <span className="font-medium text-foreground">{envSlug}</span>.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Link to={`/project/${projectSlug}/${envSlug}/create-service/docker`}>
            <Button size="sm" className="gap-1.5">
              <PlusIcon size={15} strokeWidth={2} /> New docker service
            </Button>
          </Link>
        </div>
      </div>

      <dl className="-mt-2 flex flex-wrap divide-x divide-border border-y border-border">
        {stats.map((stat) => (
          <div
            key={stat.label}
            className="flex flex-col gap-1 px-6 py-3 first:pl-0"
          >
            <dd
              className={cn(
                "font-mono text-2xl font-medium leading-none tabular-nums",
                stat.healthy && allHealthy
                  ? "text-green-600 dark:text-green-500"
                  : "text-foreground"
              )}
            >
              {stat.value}
            </dd>
            <dt className="text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground">
              {stat.label}
            </dt>
          </div>
        ))}
      </dl>

      <div className="flex flex-wrap items-center gap-2">
        <div className="flex items-center gap-1 bg-muted p-1">
          {environments.map((env) => {
            const active = env.name === envSlug;
            return (
              <Link
                key={env.id}
                to={`/project/${projectSlug}/${env.name}`}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "ease-spring inline-flex items-center gap-1.5 px-3 py-1.5 text-sm transition duration-200",
                  active
                    ? "bg-card font-medium text-foreground shadow-xs"
                    : "text-muted-foreground hover:text-foreground"
                )}
              >
                {env.name}
                {env.is_preview && (
                  <span className="bg-amber-500/10 px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide text-amber-700 ring-1 ring-amber-500/30 dark:text-amber-400">
                    preview
                  </span>
                )}
              </Link>
            );
          })}
        </div>

        <Popover>
          <PopoverTrigger asChild>
            <Button
              variant="ghost"
              size="sm"
              className="size-8 p-0"
              title="Add environment"
            >
              <PlusIcon size={16} strokeWidth={1.75} />
            </Button>
          </PopoverTrigger>
          <PopoverContent align="start" className="w-64">
            <Form method="POST" className="flex flex-col gap-2.5">
              <div className="flex flex-col gap-1.5">
                <span className="text-sm font-medium tracking-tight">
                  New environment
                </span>
                <FieldSetInput
                  name="name"
                  placeholder="staging"
                  className="h-9 font-mono text-sm"
                  required
                />
              </div>
              <Button type="submit" size="sm" className="w-full">
                Create environment
              </Button>
            </Form>
          </PopoverContent>
        </Popover>

        {deletableEnvs.length > 0 && (
          <Popover>
            <PopoverTrigger asChild>
              <Button
                variant="ghost"
                size="sm"
                className="size-8 p-0"
                title="Manage environments"
              >
                <MoreHorizontalIcon size={16} strokeWidth={1.75} />
              </Button>
            </PopoverTrigger>
            <PopoverContent align="start" className="w-64 p-2">
              <p className="px-2 py-1.5 text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground">
                Delete environment
              </p>
              <div className="flex flex-col">
                {deletableEnvs.map((env) => (
                  <Form key={env.id} method="POST">
                    <input type="hidden" name="intent" value="delete-env" />
                    <input type="hidden" name="env_name" value={env.name} />
                    <button
                      type="submit"
                      className="flex w-full items-center justify-between gap-2 px-2 py-1.5 text-sm transition-colors hover:bg-destructive/10 hover:text-destructive"
                    >
                      <span className="truncate">{env.name}</span>
                      <Trash2Icon size={14} strokeWidth={1.75} />
                    </button>
                  </Form>
                ))}
              </div>
            </PopoverContent>
          </Popover>
        )}
      </div>

      {actionData && "error" in actionData && (
        <p className="border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive">
          {actionData.error.errors.map((e) => e.detail).join("")}
        </p>
      )}

      <div className="flex flex-col gap-3">
        <div className="flex items-baseline justify-between">
          <h2 className="text-xs font-medium uppercase tracking-[0.16em] text-muted-foreground">
            Services
            {services && services.length > 0 && (
              <span className="tabular-nums"> · {services.length}</span>
            )}
          </h2>
        </div>
        {services && services.length > 0 ? (
          <Card className="divide-y divide-border overflow-hidden p-0">
            {services.map((card) => (
              <DockerServiceCard
                key={card.id}
                card={card}
                projectSlug={projectSlug}
                envSlug={envSlug}
              />
            ))}
          </Card>
        ) : (
          <Card className="relative flex flex-col items-center gap-4 overflow-hidden px-6 py-16 text-center">
            <BoxIcon
              className="pointer-events-none absolute -bottom-10 -right-8 text-foreground/[0.04]"
              size={220}
              strokeWidth={1}
              aria-hidden
            />
            <div className="relative flex flex-col gap-1.5">
              <p className="text-xl font-semibold tracking-tight">
                No services yet
              </p>
              <p className="mx-auto max-w-xs text-sm text-muted-foreground">
                Deploy your first service from a Docker image.
              </p>
            </div>
            <div className="relative flex flex-wrap items-center justify-center gap-2">
              <Link
                to={`/project/${projectSlug}/${envSlug}/create-service/docker`}
              >
                <Button size="sm" className="gap-1.5">
                  <PlusIcon size={15} strokeWidth={2} /> New docker service
                </Button>
              </Link>
            </div>
          </Card>
        )}
      </div>
    </section>
  );
}
