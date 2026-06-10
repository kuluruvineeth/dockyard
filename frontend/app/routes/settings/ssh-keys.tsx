import { useQuery } from "@tanstack/react-query";
import { KeyRoundIcon, XIcon } from "lucide-react";
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
import { sshKeysQueries } from "~/lib/queries";
import { getFormErrorsFromResponseData } from "~/lib/utils";
import { queryClient } from "~/root";
import { getCsrfTokenHeader, metaTitle } from "~/utils";
import type { Route } from "./+types/ssh-keys";

export const meta: Route.MetaFunction = () => [metaTitle("SSH keys")];

export async function clientLoader() {
  await queryClient.ensureQueryData(sshKeysQueries.list);
  return null;
}

export async function clientAction({ request }: Route.ClientActionArgs) {
  const formData = await request.formData();
  const headers = { ...(await getCsrfTokenHeader()) };

  if (formData.get("intent")?.toString() === "delete") {
    const { error } = await apiClient.DELETE("/api/ssh-keys/{slug}/", {
      headers,
      params: { path: { slug: formData.get("slug")?.toString() ?? "" } }
    });
    if (error) {
      return { error };
    }
    await queryClient.invalidateQueries({
      queryKey: sshKeysQueries.list.queryKey
    });
    return { ok: true };
  }

  const { error } = await apiClient.POST("/api/ssh-keys/", {
    headers,
    body: {
      slug: formData.get("slug")?.toString() ?? "",
      user: formData.get("user")?.toString() ?? ""
    }
  });
  if (error) {
    return { error };
  }
  await queryClient.invalidateQueries({
    queryKey: sshKeysQueries.list.queryKey
  });
  return { ok: true };
}

export default function SSHKeysPage({ actionData }: Route.ComponentProps) {
  const navigation = useNavigation();
  const isPending = navigation.state !== "idle";
  const { data: keys } = useQuery(sshKeysQueries.list);
  const errors = getFormErrorsFromResponseData(
    actionData && "error" in actionData ? actionData.error : undefined
  );

  const count = keys?.length ?? 0;

  return (
    <SettingsLayout
      title="SSH keys"
      description="Managed RSA key pairs for shell access. Add the public key to a server's authorized keys."
    >
      <SettingsSection
        title="Managed keys"
        description="Key pairs Dockyard generates and stores for shell access."
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
            {keys?.map((key) => (
              <SettingsRow
                key={key.id}
                tile={<KeyRoundIcon size={16} strokeWidth={1.75} />}
                primary={
                  <>
                    <span className="truncate font-medium tracking-tight">
                      {key.slug}
                    </span>
                    <span className="flex-none text-grey">· {key.user}</span>
                  </>
                }
                secondary={key.fingerprint ?? "No fingerprint"}
                right={
                  <Form method="POST">
                    <input type="hidden" name="intent" value="delete" />
                    <input type="hidden" name="slug" value={key.slug} />
                    <button
                      type="submit"
                      className="flex size-7 flex-none items-center justify-center text-grey transition-colors duration-150 hover:bg-destructive/10 hover:text-destructive"
                      title="Delete key"
                    >
                      <XIcon size={15} />
                    </button>
                  </Form>
                }
              />
            ))}
          </SettingsRows>
        ) : (
          <SettingsEmpty
            glyph="SSH"
            title="No SSH keys yet"
            hint="Generate a managed key pair to enable shell access."
          />
        )}

        <SettingsFormFooter label="Generate a key">
          <Form method="POST" className="flex flex-col gap-4">
            {errors.non_field_errors && (
              <p className="text-sm text-destructive">
                {errors.non_field_errors}
              </p>
            )}
            <div className="flex flex-col gap-4 sm:flex-row">
              <FieldSet
                required
                className="inline-flex flex-1 flex-col gap-1.5"
              >
                <FieldSetLabel>Name</FieldSetLabel>
                <FieldSetInput
                  name="slug"
                  placeholder="ex: deploy-key"
                  required
                />
              </FieldSet>
              <FieldSet
                required
                className="inline-flex flex-1 flex-col gap-1.5"
              >
                <FieldSetLabel>User</FieldSetLabel>
                <FieldSetInput name="user" placeholder="ex: deploy" required />
              </FieldSet>
            </div>
            <SubmitButton isPending={isPending} className="w-fit">
              Generate key
            </SubmitButton>
          </Form>
        </SettingsFormFooter>
      </SettingsSection>
    </SettingsLayout>
  );
}
