import { ArrowLeftIcon, LoaderIcon, PackageIcon } from "lucide-react";
import { Form, Link, redirect, useNavigation } from "react-router";
import { apiClient } from "~/api/client";
import { Button, SubmitButton } from "~/components/ui/button";
import { Card } from "~/components/ui/card";
import {
  FieldSet,
  FieldSetErrors,
  FieldSetInput,
  FieldSetLabel
} from "~/components/ui/fieldset";
import { environmentQueries } from "~/lib/queries";
import { getFormErrorsFromResponseData } from "~/lib/utils";
import { queryClient } from "~/root";
import { getCsrfTokenHeader, metaTitle } from "~/utils";
import type { Route } from "./+types/create-docker-service";

export const meta: Route.MetaFunction = () => [
  metaTitle("Create Docker Service")
];

export async function clientAction({
  request,
  params
}: Route.ClientActionArgs) {
  const formData = await request.formData();
  const image = formData.get("image")?.toString().trim() ?? "";
  const slug = formData.get("slug")?.toString().trim();

  const body = { image, slug: slug ? slug : undefined };
  const { error: errors } = await apiClient.POST(
    "/api/projects/{project_slug}/{env_slug}/create-service/docker/",
    {
      headers: { ...(await getCsrfTokenHeader()) },
      params: {
        path: {
          project_slug: params.projectSlug,
          env_slug: params.envSlug
        }
      },
      body
    }
  );
  if (errors) {
    return { errors, userData: body };
  }

  await queryClient.invalidateQueries({
    queryKey: environmentQueries.serviceList(params.projectSlug, params.envSlug)
      .queryKey
  });
  throw redirect(`/project/${params.projectSlug}/${params.envSlug}`);
}

export default function CreateDockerService({
  actionData,
  params
}: Route.ComponentProps) {
  const navigation = useNavigation();
  const isPending = navigation.state !== "idle";
  const errors = getFormErrorsFromResponseData(actionData?.errors);

  return (
    <section className="mx-auto flex max-w-2xl flex-col gap-6">
      <div className="flex flex-col gap-2.5">
        <Link
          to={`/project/${params.projectSlug}/${params.envSlug}`}
          className="inline-flex w-fit items-center gap-1.5 text-[11px] font-medium uppercase tracking-[0.18em] text-grey transition-colors duration-150 hover:text-foreground"
        >
          <ArrowLeftIcon size={12} strokeWidth={2} /> {params.projectSlug} /{""}
          {params.envSlug}
        </Link>
        <div className="flex min-w-0 items-center gap-3">
          <span className="flex size-9 flex-none items-center justify-center bg-muted text-foreground">
            <PackageIcon size={16} strokeWidth={1.75} />
          </span>
          <h1 className="text-3xl font-semibold tracking-tight">
            Create a Docker service
          </h1>
        </div>
        <p className="text-sm text-grey">
          Deploy a service from a prebuilt image on Docker Hub or a private
          registry.
        </p>
      </div>

      <Form method="POST" className="flex flex-col gap-6">
        <Card className="flex flex-col gap-4 p-6">
          <FieldSet
            name="image"
            errors={errors.image}
            className="flex flex-col gap-1.5"
          >
            <FieldSetLabel>Docker image</FieldSetLabel>
            <FieldSetInput
              className="font-mono"
              placeholder="ex: redis:alpine"
              defaultValue={actionData?.userData?.image}
              required
            />
            <FieldSetErrors />
          </FieldSet>

          <FieldSet
            name="slug"
            errors={errors.slug}
            className="flex flex-col gap-1.5"
          >
            <FieldSetLabel>Slug (optional)</FieldSetLabel>
            <FieldSetInput
              className="font-mono"
              placeholder="auto-generated if empty"
              defaultValue={actionData?.userData?.slug}
            />
            <FieldSetErrors />
          </FieldSet>

          {errors.non_field_errors && (
            <p className="text-sm text-destructive">
              {errors.non_field_errors}
            </p>
          )}
        </Card>

        <div className="flex items-center justify-end gap-2">
          <Link to={`/project/${params.projectSlug}/${params.envSlug}`}>
            <Button variant="outline">Cancel</Button>
          </Link>
          <SubmitButton isPending={isPending} className="gap-2">
            {isPending ? (
              <>
                <span>Creating…</span>
                <LoaderIcon className="animate-spin" size={15} />
              </>
            ) : (
              "Create service"
            )}
          </SubmitButton>
        </div>
      </Form>
    </section>
  );
}
