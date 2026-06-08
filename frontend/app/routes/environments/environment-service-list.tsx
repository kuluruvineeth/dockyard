import { useQuery } from "@tanstack/react-query";
import { BoxIcon, PlusIcon } from "lucide-react";
import { Link } from "react-router";
import { DockerServiceCard } from "~/components/service-cards";
import { Button } from "~/components/ui/button";
import { Card } from "~/components/ui/card";
import { environmentQueries } from "~/lib/queries";
import { cn } from "~/lib/utils";
import { queryClient } from "~/root";
import { metaTitle } from "~/utils";
import type { Route } from "./+types/environment-service-list";

export const meta: Route.MetaFunction = ({ params }) => [
  metaTitle(`${params.projectSlug} / ${params.envSlug}`)
];

export async function clientLoader({ params }: Route.ClientLoaderArgs) {
  await queryClient.ensureQueryData(
    environmentQueries.serviceList(params.projectSlug, params.envSlug)
  );
  return null;
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
  params
}: Route.ComponentProps) {
  const { projectSlug, envSlug } = params;
  const { data: services } = useQuery(
    environmentQueries.serviceList(projectSlug, envSlug)
  );

  if (!services) return <EnvironmentServiceListSkeleton />;

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
            Services running in{" "}
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
