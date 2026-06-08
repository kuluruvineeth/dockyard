import { queryOptions } from "@tanstack/react-query";
import { apiClient } from "~/api/client";
import { durationToMs } from "~/utils";

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
