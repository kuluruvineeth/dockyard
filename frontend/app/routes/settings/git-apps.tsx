import { useQuery } from "@tanstack/react-query";
import { GitBranchIcon } from "lucide-react";
import type { ApiResponse } from "~/api/client";
import {
  SettingsEmpty,
  SettingsLayout,
  SettingsRow,
  SettingsRows,
  SettingsSection
} from "~/components/settings-nav";
import { StatusBadge } from "~/components/status-badge";
import { Button } from "~/components/ui/button";
import { gitAppsQueries } from "~/lib/queries";
import { queryClient } from "~/root";
import { metaTitle } from "~/utils";
import type { Route } from "./+types/git-apps";

export const meta: Route.MetaFunction = () => [metaTitle("Git apps")];

export async function clientLoader() {
  await queryClient.ensureQueryData(gitAppsQueries.list);
  return null;
}

type GitApp = ApiResponse<"get", "/api/connectors/git-apps/">[number];

export default function GitAppsPage() {
  const { data: apps } = useQuery(gitAppsQueries.list);

  const count = apps?.length ?? 0;

  return (
    <SettingsLayout
      title="Git apps"
      description="Connect GitHub or GitLab to deploy private repositories and auto-deploy on push."
    >
      <SettingsSection
        title="Connect a provider"
        description="Authorize Dockyard to read your repositories and receive push events."
      >
        <div className="px-5 py-5">
          <div className="flex flex-wrap gap-2">
            <Button type="button" variant="outline" className="gap-1.5">
              <GitBranchIcon size={15} strokeWidth={1.75} /> Connect GitHub
            </Button>
            <Button type="button" variant="outline" className="gap-1.5">
              <GitBranchIcon size={15} strokeWidth={1.75} /> Connect GitLab
            </Button>
          </div>
        </div>
      </SettingsSection>

      <SettingsSection
        title="Connected apps"
        description="Providers already authorized for this instance."
        action={
          count > 0 ? (
            <span className="bg-muted px-1.5 py-0.5 text-[11px] font-medium tabular-nums text-grey">
              {count}
            </span>
          ) : undefined
        }
      >
        {count > 0 ? (
          <SettingsRows>
            {apps?.map((app) => (
              <GitAppRow key={app.id} app={app} />
            ))}
          </SettingsRows>
        ) : (
          <SettingsEmpty
            glyph="GIT"
            title="No git apps connected"
            hint="Connect a provider to deploy from private repositories and trigger deploys on every push."
          />
        )}
      </SettingsSection>
    </SettingsLayout>
  );
}

function GitAppRow({ app }: { app: GitApp }) {
  const isGithub = app.github !== null;
  const inner = app.github ?? app.gitlab;
  if (inner === null) return null;
  const installed = inner.is_installed;
  const repoCount = inner.repositories.length;

  return (
    <SettingsRow
      tileNeutral
      tile={<GitBranchIcon size={17} strokeWidth={1.75} />}
      primary={
        <span className="truncate font-medium tracking-tight">
          {inner.name}
        </span>
      }
      secondary={
        <span className="tabular-nums">
          {isGithub ? "GitHub" : "GitLab"} ·{" "}
          {repoCount === 1 ? "1 repository" : `${repoCount} repositories`}
        </span>
      }
      right={
        <StatusBadge
          color={installed ? "green" : "yellow"}
          pingState={installed ? "static" : "hidden"}
        >
          {installed ? "Installed" : "Pending install"}
        </StatusBadge>
      }
    />
  );
}
