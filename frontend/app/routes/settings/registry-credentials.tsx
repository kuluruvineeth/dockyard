import { useQuery } from "@tanstack/react-query";
import { PlusIcon, XIcon } from "lucide-react";
import { Form, useNavigation } from "react-router";
import { apiClient } from "~/api/client";
import {
  SettingsEmpty,
  SettingsFormFooter,
  SettingsLayout,
  SettingsRow,
  SettingsRows,
  SettingsSection
} from "~/components/settings-nav";
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

const REGISTRY_META: Record<string, { monogram: string; label: string }> = {
  GENERIC: { monogram: "REG", label: "Generic" },
  DOCKER_HUB: { monogram: "DH", label: "Docker Hub" },
  GITHUB: { monogram: "GH", label: "GitHub" },
  GITLAB: { monogram: "GL", label: "GitLab" },
  GOOGLE_ARTIFACT: { monogram: "GAR", label: "Google Artifact" },
  AWS_ECR: { monogram: "ECR", label: "AWS ECR" }
};

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
    <SettingsLayout
      title="Registry credentials"
      description="Credentials for pulling private images from container registries."
    >
      <SettingsSection
        title="Saved credentials"
        description="Reusable across every service that pulls a private image."
        action={
          count > 0 ? (
            <span className="bg-muted px-1.5 py-0.5 text-[11px] font-medium tabular-nums text-grey">
              {count}
            </span>
          ) : undefined
        }
      >
        {count === 0 ? (
          <SettingsEmpty
            glyph="REG"
            title="No credentials yet"
            hint="Add credentials below to pull private images from your container registries."
          />
        ) : (
          <SettingsRows>
            {credentials?.map((cred) => {
              const meta = REGISTRY_META[cred.registry_type] ?? {
                monogram: "REG",
                label: cred.registry_type
              };
              return (
                <SettingsRow
                  key={cred.id}
                  tile={
                    <span className="font-mono text-[10px] font-semibold tracking-tight">
                      {meta.monogram}
                    </span>
                  }
                  primary={
                    <>
                      <span className="truncate font-medium tracking-tight">
                        {cred.name}
                      </span>
                      <span className="flex-none bg-muted px-1.5 py-0.5 text-[11px] font-medium text-grey">
                        {meta.label}
                      </span>
                    </>
                  }
                  secondary={`${cred.username} @ ${cred.url}`}
                  right={
                    <Form method="POST">
                      <input type="hidden" name="intent" value="delete" />
                      <input
                        type="hidden"
                        name="credential_id"
                        value={cred.id}
                      />
                      <button
                        type="submit"
                        className="flex size-7 flex-none items-center justify-center text-grey transition-colors duration-150 hover:bg-destructive/10 hover:text-destructive"
                        title="Delete"
                      >
                        <XIcon size={15} strokeWidth={1.75} />
                      </button>
                    </Form>
                  }
                />
              );
            })}
          </SettingsRows>
        )}

        <SettingsFormFooter label="Add credentials">
          <Form method="POST" className="flex flex-col gap-4">
            {errors.non_field_errors && (
              <p className="text-sm text-destructive">
                {errors.non_field_errors}
              </p>
            )}
            <div className="flex flex-col gap-4 md:flex-row">
              <FieldSet
                required
                className="inline-flex flex-1 flex-col gap-1.5"
              >
                <FieldSetLabel>Name</FieldSetLabel>
                <FieldSetInput name="name" placeholder="ex: ghcr" required />
              </FieldSet>
              <FieldSet className="inline-flex flex-col gap-1.5">
                <FieldSetLabel>Type</FieldSetLabel>
                <select
                  name="registry_type"
                  defaultValue="GENERIC"
                  className="h-10 border border-input bg-background px-3 transition-colors duration-150 hover:border-foreground/15"
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
            <div className="flex flex-col gap-4 md:flex-row">
              <FieldSet
                required
                className="inline-flex flex-1 flex-col gap-1.5"
              >
                <FieldSetLabel>Username</FieldSetLabel>
                <FieldSetInput name="username" required />
              </FieldSet>
              <FieldSet
                required
                className="inline-flex flex-1 flex-col gap-1.5"
              >
                <FieldSetLabel>Password / token</FieldSetLabel>
                <FieldSetInput name="password" type="password" required />
                <span className="text-xs text-grey">
                  Stored encrypted and never shown again.
                </span>
              </FieldSet>
            </div>
            <SubmitButton isPending={isPending} className="w-fit gap-1.5">
              <PlusIcon size={15} strokeWidth={2} /> Add credentials
            </SubmitButton>
          </Form>
        </SettingsFormFooter>
      </SettingsSection>
    </SettingsLayout>
  );
}
