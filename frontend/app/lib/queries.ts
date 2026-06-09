import { queryOptions } from "@tanstack/react-query";
import { apiClient } from "~/api/client";
import { notFound } from "~/lib/utils";
import { durationToMs } from "~/utils";

export const projectQueries = {
  list: (slug?: string) =>
    queryOptions({
      queryKey: ["PROJECT_LIST", slug ?? ""] as const,
      queryFn: async ({ signal }) => {
        const { data } = await apiClient.GET("/api/projects/", {
          params: { query: slug ? { slug } : {} },
          signal
        });
        return data ?? [];
      }
    }),
  single: (slug: string) =>
    queryOptions({
      queryKey: ["PROJECT", slug] as const,
      queryFn: async ({ signal }) => {
        const { data, error } = await apiClient.GET("/api/projects/{slug}/", {
          params: { path: { slug } },
          signal
        });
        if (error) {
          throw notFound(`Project \`${slug}\` not found`);
        }
        return data;
      }
    })
};

export const userQueries = {
  authedUser: queryOptions({
    queryKey: ["AUTHED_USER"] as const,
    queryFn: async ({ signal }) => {
      const { data } = await apiClient.GET("/api/auth/me", { signal });
      return data?.user ?? null;
    },
    // Never served stale. This is the gate the dashboard loader trusts, and a
    // 30 minute window meant a dead session still looked signed in.
    staleTime: 0
  }),
  checkUserExistence: queryOptions({
    queryKey: ["CHECK_USER_EXISTENCE"] as const,
    queryFn: async ({ signal }) => {
      const { data, error } = await apiClient.GET(
        "/api/auth/check-user-existence",
        { signal }
      );
      if (error) {
        throw new Error("Failed to check whether a user exists");
      }
      return data;
    }
  })
};

export const environmentQueries = {
  serviceList: (projectSlug: string, envSlug: string, query?: string) =>
    queryOptions({
      queryKey: ["SERVICE_LIST", projectSlug, envSlug, query ?? ""] as const,
      queryFn: async ({ signal }) => {
        const { data } = await apiClient.GET(
          "/api/projects/{project_slug}/{env_slug}/service-list/",
          {
            params: {
              path: { project_slug: projectSlug, env_slug: envSlug },
              query: query ? { query } : {}
            },
            signal
          }
        );
        return data ?? [];
      }
    })
};

// A deployment that is still moving. While any of these is the newest one,
// the page polls, because the whole point of watching a deploy is watching it
// change — otherwise the UI sits on "Queued" for the length of a build.
const IN_FLIGHT_STATUSES = [
  "QUEUED",
  "PREPARING",
  "BUILDING",
  "STARTING",
  "RESTARTING",
  "CANCELLING"
];

const POLL_WHILE_DEPLOYING = 2000;

function pollWhileInFlight(statuses: Array<string | undefined>) {
  return statuses.some((s) => s && IN_FLIGHT_STATUSES.includes(s))
    ? POLL_WHILE_DEPLOYING
    : false;
}

export const serviceQueries = {
  single: (projectSlug: string, envSlug: string, slug: string) =>
    queryOptions({
      queryKey: ["SERVICE", projectSlug, envSlug, slug] as const,
      queryFn: async ({ signal }) => {
        const { data, error } = await apiClient.GET(
          "/api/projects/{project_slug}/{env_slug}/service-details/{slug}/",
          {
            params: {
              path: {
                project_slug: projectSlug,
                env_slug: envSlug,
                slug
              }
            },
            signal
          }
        );
        if (error) {
          throw notFound(`Service \`${slug}\` not found`);
        }
        return data;
      },
      refetchInterval: (query) =>
        pollWhileInFlight([
          (query.state.data as { status?: string } | undefined)?.status
        ])
    }),
  deployments: (projectSlug: string, envSlug: string, slug: string) =>
    queryOptions({
      queryKey: ["DEPLOYMENTS", projectSlug, envSlug, slug] as const,
      queryFn: async ({ signal }) => {
        const { data } = await apiClient.GET(
          "/api/projects/{project_slug}/{env_slug}/service-details/{slug}/deployments/",
          {
            params: {
              path: {
                project_slug: projectSlug,
                env_slug: envSlug,
                slug
              }
            },
            signal
          }
        );
        return data?.results ?? [];
      },
      refetchInterval: (query) =>
        pollWhileInFlight(
          ((query.state.data as Array<{ status?: string }> | undefined) ?? [])
            .slice(0, 3)
            .map((d) => d.status)
        )
    })
};

export const dockerHubQueries = {
  images: (query: string) =>
    queryOptions({
      queryKey: ["DOCKER_HUB_IMAGES", query] as const,
      queryFn: async ({ signal }) => {
        if (!query) return [];
        const { data } = await apiClient.GET("/api/docker/image-search/", {
          params: { query: { q: query } },
          signal
        });
        return data?.images ?? [];
      },
      enabled: query.length > 0
    })
};

export const serverQueries = {
  settings: queryOptions({
    queryKey: ["SETTINGS"] as const,
    queryFn: async ({ signal }) => {
      const { data } = await apiClient.GET("/api/settings", { signal });
      return data;
    }
  }),
  resourceLimits: queryOptions({
    queryKey: ["RESOURCE_LIMITS"] as const,
    queryFn: async ({ signal }) => {
      const { data } = await apiClient.GET("/api/server/resource-limits", {
        signal
      });
      return data;
    }
  })
};
