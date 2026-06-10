import { redirect } from "react-router";
import { getCsrfTokenHeader } from "~/utils";
import type { Route } from "./+types/git-apps-github-setup";

export async function clientLoader({ request }: Route.ClientLoaderArgs) {
  const url = new URL(request.url);
  const code = url.searchParams.get("code");
  const installationId = url.searchParams.get("installation_id");
  const state = url.searchParams.get("state");

  const csrf = await getCsrfTokenHeader();
  const headers: HeadersInit = {
    "Content-Type": "application/json",
    "X-CSRFToken": csrf["X-CSRFToken"] ?? ""
  };

  if (code) {
    await fetch("/api/connectors/github/setup/", {
      method: "POST",
      headers,
      body: JSON.stringify({ code }),
      redirect: "manual"
    });
  } else if (installationId && state) {
    await fetch("/api/connectors/github/setup/", {
      method: "POST",
      headers,
      body: JSON.stringify({
        state,
        installation_id: Number(installationId)
      }),
      redirect: "manual"
    });
  }

  return redirect("/settings/git-apps");
}

export default function GithubSetup() {
  return null;
}
