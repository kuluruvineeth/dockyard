import { useState } from "react";
import { Button, SubmitButton } from "~/components/ui/button";
import {
  FieldSet,
  FieldSetInput,
  FieldSetLabel
} from "~/components/ui/fieldset";
import { cn } from "~/lib/utils";

export function GithubMark({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="currentColor"
      aria-hidden
      className={className}
    >
      <path d="M12 .297c-6.63 0-12 5.373-12 12 0 5.303 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61C4.422 18.07 3.633 17.7 3.633 17.7c-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 22.092 24 17.592 24 12.297c0-6.627-5.373-12-12-12" />
    </svg>
  );
}

export function GitlabMark({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="currentColor"
      aria-hidden
      className={className}
    >
      <path d="M23.955 13.587l-1.342-4.135-2.664-8.189a.455.455 0 00-.867 0L16.418 9.45H7.582L4.918 1.263a.455.455 0 00-.867 0L1.386 9.45.044 13.587a.924.924 0 00.331 1.03l11.625 8.443 11.624-8.443a.924.924 0 00.331-1.03z" />
    </svg>
  );
}

function connectGithub() {
  const origin = window.location.origin;
  const manifest = JSON.stringify({
    name: "Dockyard",
    url: origin,
    hook_attributes: { url: `${origin}/api/connectors/github/webhook/` },
    redirect_url: `${origin}/settings/git-apps/github/setup`,
    public: false,
    default_permissions: {
      contents: "read",
      metadata: "read",
      pull_requests: "write"
    },
    default_events: ["push", "pull_request"]
  });

  const form = document.createElement("form");
  form.method = "post";
  form.action = "https://github.com/settings/apps/new";
  const input = document.createElement("input");
  input.type = "hidden";
  input.name = "manifest";
  input.value = manifest;
  form.appendChild(input);
  document.body.appendChild(form);
  form.submit();
}

function ProviderCard({
  mark,
  name,
  description,
  active,
  children
}: {
  mark: React.ReactNode;
  name: string;
  description: string;
  active?: boolean;
  children: React.ReactNode;
}) {
  return (
    <div
      className={cn(
        "flex flex-col gap-4 border bg-card p-5 shadow-xs transition-colors duration-150",
        active
          ? "border-foreground/30"
          : "border-border hover:border-foreground/15"
      )}
    >
      <div className="flex items-center gap-3">
        <span className="flex size-9 flex-none items-center justify-center bg-foreground/[0.04] text-foreground ring-1 ring-border">
          {mark}
        </span>
        <div className="flex min-w-0 flex-col">
          <span className="font-medium tracking-tight">{name}</span>
          <span className="text-[13px] text-grey">{description}</span>
        </div>
      </div>
      <div className="mt-auto">{children}</div>
    </div>
  );
}

export function GitConnect() {
  const [gitlabOpen, setGitlabOpen] = useState(false);

  function startGitlab(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const gitlabUrl =
      (data.get("gitlab_url") as string) || "https://gitlab.com";
    const appId = data.get("app_id") as string;
    const secret = data.get("secret") as string;
    const name = (data.get("name") as string) || "Dockyard";
    const redirectUri = `${window.location.origin}/settings/git-apps/gitlab/setup`;

    sessionStorage.setItem(
      "dky_gitlab_connect",
      JSON.stringify({
        name,
        gitlab_url: gitlabUrl,
        app_id: appId,
        secret,
        redirect_uri: redirectUri
      })
    );

    const authorize =
      `${gitlabUrl}/oauth/authorize?client_id=${encodeURIComponent(appId)}` +
      `&redirect_uri=${encodeURIComponent(redirectUri)}` +
      `&response_type=code&scope=api`;
    window.location.href = authorize;
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="grid gap-3 sm:grid-cols-2">
        <ProviderCard
          mark={<GithubMark className="size-[18px]" />}
          name="GitHub"
          description="Deploy private repos and auto-deploy on push."
        >
          <Button type="button" className="w-full" onClick={connectGithub}>
            Connect GitHub
          </Button>
        </ProviderCard>

        <ProviderCard
          mark={<GitlabMark className="size-[18px]" />}
          name="GitLab"
          description="Bring your own OAuth app to deploy from GitLab."
          active={gitlabOpen}
        >
          <Button
            type="button"
            variant={gitlabOpen ? "outline" : "default"}
            className="w-full"
            onClick={() => setGitlabOpen((open) => !open)}
          >
            {gitlabOpen ? "Cancel" : "Connect GitLab"}
          </Button>
        </ProviderCard>
      </div>

      {gitlabOpen && (
        <form
          onSubmit={startGitlab}
          className="flex flex-col gap-4 border border-border bg-card p-5 shadow-xs"
        >
          <p className="text-[13px] text-grey">
            Create a GitLab OAuth application (scope <code>api</code>), then
            paste its credentials here to authorize Dockyard.
          </p>
          <div className="flex flex-col gap-4 sm:flex-row">
            <FieldSet className="flex-1 inline-flex flex-col gap-1.5">
              <FieldSetLabel>GitLab URL</FieldSetLabel>
              <FieldSetInput
                name="gitlab_url"
                placeholder="https://gitlab.com"
              />
            </FieldSet>
            <FieldSet required className="flex-1 inline-flex flex-col gap-1.5">
              <FieldSetLabel>Application ID</FieldSetLabel>
              <FieldSetInput name="app_id" required />
            </FieldSet>
          </div>
          <FieldSet required className="inline-flex flex-col gap-1.5">
            <FieldSetLabel>Secret</FieldSetLabel>
            <FieldSetInput name="secret" type="password" required />
            <span className="text-xs text-grey">
              Stored encrypted and never shown again.
            </span>
          </FieldSet>
          <SubmitButton isPending={false} className="w-fit">
            Authorize on GitLab
          </SubmitButton>
        </form>
      )}
    </div>
  );
}
