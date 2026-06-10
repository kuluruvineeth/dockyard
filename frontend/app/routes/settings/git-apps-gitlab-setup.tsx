import { redirect } from "react-router";
import { getCsrfTokenHeader } from "~/utils";
import type { Route } from "./+types/git-apps-gitlab-setup";

export async function clientLoader({ request }: Route.ClientLoaderArgs) {
  const url = new URL(request.url);
  const code = url.searchParams.get("code");
  const stored = sessionStorage.getItem("dky_gitlab_connect");

  if (code && stored) {
    sessionStorage.removeItem("dky_gitlab_connect");
    const creds = JSON.parse(stored);
    const csrf = await getCsrfTokenHeader();
    const headers: HeadersInit = {
      "Content-Type": "application/json",
      "X-CSRFToken": csrf["X-CSRFToken"] ?? ""
    };
    await fetch("/api/connectors/gitlab/setup/", {
      method: "POST",
      headers,
      body: JSON.stringify({ ...creds, code }),
      redirect: "manual"
    });
  }

  return redirect("/settings/git-apps");
}

export default function GitlabSetup() {
  return null;
}
