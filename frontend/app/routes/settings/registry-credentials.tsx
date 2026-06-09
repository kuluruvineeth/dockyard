import { useQuery } from "@tanstack/react-query";
import { ArrowLeftIcon, KeyRoundIcon, PlusIcon, XIcon } from "lucide-react";
import { Form, Link, useNavigation } from "react-router";
import { apiClient } from "~/api/client";
import { SubmitButton } from "~/components/ui/button";
import {
  FieldSet,
  FieldSetInput,
  FieldSetLabel
} from "~/components/ui/fieldset";
import { registryQueries } from "~/lib/queries";
import { getFormErrorsFromResponseData } from "~/lib/utils";
import { queryClient } from "~/root";
import { getCsrfTokenHeader, metaTitle } from "~/utils";
import type { Route } from "./+types/registry-credentials";

export const meta: Route.MetaFunction = () => [metaTitle("Settings")];

export async function clientLoader() {
  await queryClient.ensureQueryData(registryQueries.list);
  return null;
}

export async function clientAction({ request }: Route.ClientActionArgs) {
  const formData = await request.formData();
  const headers = { ...(await getCsrfTokenHeader()) };

  if (formData.get("intent")?.toString() === "delete") {
    const { error } = await apiClient.DELETE(
      "/api/registry-credentials/{credential_id}/",
      {
        headers,
        params: {
          path: {
            credential_id: formData.get("credential_id")?.toString() ?? ""
          }
        }
      }
    );
    if (error) {
      return { error };
    }
    await queryClient.invalidateQueries({
      queryKey: registryQueries.list.queryKey
    });
    return { ok: true };
  }

  const { error } = await apiClient.POST("/api/registry-credentials/", {
    headers,
    body: {
      name: formData.get("name")?.toString() ?? "",
      url: formData.get("url")?.toString() ?? "",
      username: formData.get("username")?.toString() ?? "",
      password: formData.get("password")?.toString() ?? "",
      registry_type: formData.get("registry_type")?.toString() || "GENERIC"
    }
  });
  if (error) {
    return { error };
  }
  await queryClient.invalidateQueries({
    queryKey: registryQueries.list.queryKey
  });
  return { ok: true };
}

export default function RegistryCredentialsPage({
  actionData
}: Route.ComponentProps) {
  const navigation = useNavigation();
  const isPending = navigation.state !== "idle";
  const { data: credentials } = useQuery(registryQueries.list);
  const errors = getFormErrorsFromResponseData(
    actionData && "error" in actionData ? actionData.error : undefined
  );

  const count = credentials?.length ?? 0;

  return (
    <section className="flex flex-col gap-8 max-w-2xl">
      <div className="flex flex-col gap-2.5">
        <Link
          to="/"
          className="inline-flex w-fit items-center gap-1.5 text-[11px] font-medium uppercase tracking-[0.18em] text-grey transition-colors duration-150 hover:text-foreground"
        >
          <ArrowLeftIcon size={12} strokeWidth={2} /> Projects
        </Link>
        <h1 className="text-3xl font-semibold tracking-tight">
          Registry credentials
        </h1>
        <p className="text-sm text-grey">
          Credentials for pulling private images from container registries.
        </p>
      </div>

      <div className="flex flex-col gap-4">
        <h2 className="text-xs font-medium uppercase tracking-[0.16em] text-grey">
          Saved credentials
          {count > 0 ? ` · ${count}` : ""}
        </h2>

        {count === 0 ? (
          <div className="flex flex-col items-center gap-5 border border-dashed border-foreground/15 px-6 py-16 text-center">
            <span className="flex size-12 items-center justify-center bg-primary/10 text-primary ring-1 ring-primary/15">
              <KeyRoundIcon size={22} strokeWidth={1.5} />
            </span>
            <div className="flex flex-col gap-1.5">
              <p className="font-medium tracking-tight">No credentials yet</p>
              <p className="mx-auto max-w-xs text-sm text-grey">
                Add credentials below to pull private images from your container
                registries.
              </p>
            </div>
          </div>
        ) : (
          <div className="flex flex-col gap-2.5">
            {credentials?.map((cred) => (
              <div
                key={cred.id}
                className="flex items-center justify-between gap-3 border border-border bg-background p-4 shadow-xs transition-colors duration-150 hover:border-foreground/15 hover:bg-foreground/[0.015]"
              >
                <div className="flex items-center gap-3 min-w-0">
                  <span className="flex size-9 flex-none items-center justify-center bg-primary/10 text-primary ring-1 ring-primary/15">
                    <KeyRoundIcon size={16} strokeWidth={1.75} />
                  </span>
                  <div className="flex flex-col min-w-0">
                    <span className="flex items-center gap-2 min-w-0">
                      <span className="font-medium tracking-tight truncate">
                        {cred.name}
                      </span>
                      <span className="rounded-full bg-foreground/[0.06] px-2 py-0.5 text-[11px] font-medium text-grey">
                        {cred.registry_type}
                      </span>
                    </span>
                    <span className="font-mono text-xs text-grey truncate">
                      {cred.username} @ {cred.url}
                    </span>
                  </div>
                </div>
                <Form method="POST">
                  <input type="hidden" name="intent" value="delete" />
                  <input type="hidden" name="credential_id" value={cred.id} />
                  <button
                    type="submit"
                    className="flex size-7 flex-none items-center justify-center text-grey transition-colors duration-150 hover:bg-foreground/[0.06] hover:text-red-500"
                    title="Delete"
                  >
                    <XIcon size={15} strokeWidth={1.75} />
                  </button>
                </Form>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="flex flex-col gap-4">
        <h2 className="text-xs font-medium uppercase tracking-[0.16em] text-grey">
          Add credentials
        </h2>
        <Form
          method="POST"
          className="flex flex-col gap-4 border border-border bg-background p-6"
        >
          {errors.non_field_errors && (
            <p className="text-red-500 text-sm">{errors.non_field_errors}</p>
          )}
          <div className="flex flex-col md:flex-row gap-4">
            <FieldSet required className="flex-1 inline-flex flex-col gap-1.5">
              <FieldSetLabel>Name</FieldSetLabel>
              <FieldSetInput name="name" placeholder="ex: ghcr" required />
            </FieldSet>
            <FieldSet className="inline-flex flex-col gap-1.5">
              <FieldSetLabel>Type</FieldSetLabel>
              <select
                name="registry_type"
                defaultValue="GENERIC"
                className="border border-border px-3 py-2 bg-transparent transition-colors duration-150 hover:border-foreground/15"
              >
                <option value="GENERIC">Generic</option>
                <option value="DOCKER_HUB">Docker Hub</option>
                <option value="GITHUB">GitHub</option>
                <option value="GITLAB">GitLab</option>
                <option value="GOOGLE_ARTIFACT">Google Artifact</option>
                <option value="AWS_ECR">AWS ECR</option>
              </select>
            </FieldSet>
          </div>
          <FieldSet required className="flex flex-col gap-1.5">
            <FieldSetLabel>Registry URL</FieldSetLabel>
            <FieldSetInput
              name="url"
              placeholder="ex: https://ghcr.io"
              required
            />
          </FieldSet>
          <div className="flex flex-col md:flex-row gap-4">
            <FieldSet required className="flex-1 inline-flex flex-col gap-1.5">
              <FieldSetLabel>Username</FieldSetLabel>
              <FieldSetInput name="username" required />
            </FieldSet>
            <FieldSet required className="flex-1 inline-flex flex-col gap-1.5">
              <FieldSetLabel>Password / token</FieldSetLabel>
              <FieldSetInput name="password" type="password" required />
            </FieldSet>
          </div>
          <SubmitButton isPending={isPending} className="w-fit gap-1.5">
            <PlusIcon size={15} strokeWidth={2} /> Add credentials
          </SubmitButton>
        </Form>
      </div>
    </section>
  );
}
