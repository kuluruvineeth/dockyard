import { ArrowLeftIcon, LoaderIcon } from "lucide-react";
import { Form, Link, redirect, useNavigation } from "react-router";
import { apiClient } from "~/api/client";
import { SubmitButton } from "~/components/ui/button";
import {
  FieldSet,
  FieldSetErrors,
  FieldSetInput,
  FieldSetLabel,
  FieldSetTextarea
} from "~/components/ui/fieldset";
import { projectQueries } from "~/lib/queries";
import { getFormErrorsFromResponseData } from "~/lib/utils";
import { queryClient } from "~/root";
import { getCsrfTokenHeader, metaTitle } from "~/utils";
import type { Route } from "./+types/create-project";

export const meta: Route.MetaFunction = () => [metaTitle("Create Project")];

export async function clientAction({ request }: Route.ClientActionArgs) {
  const formData = await request.formData();
  const slug = formData.get("slug")?.toString().trim();
  const description = formData.get("description")?.toString().trim();

  const body = {
    slug: slug ? slug : undefined,
    description: description ? description : undefined
  };

  const { error: errors } = await apiClient.POST("/api/projects/", {
    headers: { ...(await getCsrfTokenHeader()) },
    body
  });
  if (errors) {
    return { errors, userData: body };
  }

  await queryClient.invalidateQueries({
    queryKey: projectQueries.list().queryKey
  });
  throw redirect("/");
}

export default function CreateProject({ actionData }: Route.ComponentProps) {
  const navigation = useNavigation();
  const isPending = navigation.state !== "idle";
  const errors = getFormErrorsFromResponseData(actionData?.errors);

  return (
    <section className="max-w-2xl mx-auto flex flex-col gap-6">
      <div className="flex flex-col gap-2.5">
        <Link
          to="/"
          className="inline-flex w-fit items-center gap-1.5 text-[11px] font-medium uppercase tracking-[0.18em] text-muted-foreground transition-colors duration-150 hover:text-foreground"
        >
          <ArrowLeftIcon size={12} strokeWidth={2} /> Projects
        </Link>
        <h1 className="text-3xl font-bold tracking-tighter">
          Create a new project
        </h1>
        <p className="text-sm text-muted-foreground">
          Group and deploy your services and compose stacks under one project.
        </p>
      </div>

      <Form method="POST" className="flex flex-col gap-6">
        <div className="flex flex-col gap-5 border border-border bg-card p-6 shadow-xs">
          <FieldSet
            name="slug"
            errors={errors.slug}
            className="flex flex-col gap-1.5"
          >
            <FieldSetLabel>Slug</FieldSetLabel>
            <FieldSetInput
              placeholder="ex: my-project"
              className="font-mono"
              defaultValue={actionData?.userData?.slug}
            />
            <p className="text-xs text-muted-foreground">
              Lowercase name used in URLs. Leave blank to generate one.
            </p>
            <FieldSetErrors />
          </FieldSet>

          <FieldSet
            name="description"
            errors={errors.description}
            className="flex flex-col gap-1.5"
          >
            <FieldSetLabel>Description</FieldSetLabel>
            <FieldSetTextarea
              placeholder="Optional description"
              defaultValue={actionData?.userData?.description}
            />
            <FieldSetErrors />
          </FieldSet>

          {errors.non_field_errors && (
            <p className="border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive">
              {errors.non_field_errors}
            </p>
          )}
        </div>

        <SubmitButton isPending={isPending} className="gap-2 w-fit">
          {isPending ? (
            <>
              <span>Creating...</span>
              <LoaderIcon className="animate-spin" size={15} />
            </>
          ) : (
            "Create project"
          )}
        </SubmitButton>
      </Form>
    </section>
  );
}
