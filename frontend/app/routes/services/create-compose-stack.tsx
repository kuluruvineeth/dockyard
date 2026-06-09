import { ArrowLeftIcon, LayersIcon, LoaderIcon } from "lucide-react";
import { Form, Link, redirect, useNavigation } from "react-router";
import { apiClient } from "~/api/client";
import { Code } from "~/components/code";
import { Button, SubmitButton } from "~/components/ui/button";
import { Card } from "~/components/ui/card";
import {
  FieldSet,
  FieldSetErrors,
  FieldSetInput,
  FieldSetLabel,
  FieldSetTextarea
} from "~/components/ui/fieldset";
import { environmentQueries } from "~/lib/queries";
import { getFormErrorsFromResponseData } from "~/lib/utils";
import { queryClient } from "~/root";
import { getCsrfTokenHeader, metaTitle } from "~/utils";
import type { Route } from "./+types/create-compose-stack";

export const meta: Route.MetaFunction = () => [
  metaTitle("Create Compose Stack")
];

const EXAMPLE = `services:
  web:
    image: nginx:alpine
    ports:
      -"8080:80"
  cache:
    image: redis:alpine`;

export async function clientAction({
  request,
  params
}: Route.ClientActionArgs) {
  const formData = await request.formData();
  const slug = formData.get("slug")?.toString().trim();
  const body = {
    slug: slug ?? "",
    contents: formData.get("contents")?.toString() ?? ""
  };
  const { error: errors } = await apiClient.POST(
    "/api/projects/{project_slug}/{env_slug}/create-compose-stack/",
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

export default function CreateComposeStack({
  actionData,
  params
}: Route.ComponentProps) {
  const navigation = useNavigation();
  const isPending = navigation.state !== "idle";
  const errors = getFormErrorsFromResponseData(actionData?.errors);
  const backHref = `/project/${params.projectSlug}/${params.envSlug}`;

  return (
    <section className="mx-auto flex max-w-5xl flex-col gap-6">
      <div className="flex flex-col gap-2.5">
        <Link
          to={backHref}
          className="inline-flex w-fit items-center gap-1.5 text-[11px] font-medium uppercase tracking-[0.18em] text-grey transition-colors duration-150 hover:text-foreground"
        >
          <ArrowLeftIcon size={12} strokeWidth={2} />
          <span className="font-mono normal-case tracking-normal">
            {params.projectSlug} / {params.envSlug}
          </span>
        </Link>
        <div className="flex min-w-0 items-center gap-3">
          <span className="flex size-9 flex-none items-center justify-center bg-muted text-muted-foreground">
            <LayersIcon size={16} strokeWidth={1.75} />
          </span>
          <h1 className="text-3xl font-semibold tracking-tight">
            Create a Compose stack
          </h1>
        </div>
        <p className="text-sm text-grey">
          Each service with an <Code>image</Code> becomes a deployable service.
        </p>
      </div>

      <Form
        method="POST"
        className="grid gap-6 lg:grid-cols-[1fr_320px] lg:items-start"
      >
        <FieldSet
          name="contents"
          errors={errors.contents}
          className="order-2 flex flex-col gap-2 lg:order-1"
        >
          <div className="overflow-hidden border border-white/10 bg-[#0a0a0a] shadow-xs transition-colors focus-within:border-white/20">
            <div className="flex items-center justify-between gap-3 border-b border-white/10 px-4 py-2.5">
              <FieldSetLabel className="font-mono text-xs text-white/50 dark:text-white/50">
                docker-compose.yml
              </FieldSetLabel>
              <span className="font-mono text-[11px] uppercase tracking-[0.14em] text-white/40">
                compose
              </span>
            </div>
            <FieldSetTextarea
              className="min-h-[420px] resize-y -none border-0 bg-transparent px-4 py-3 font-mono text-[13px] leading-relaxed text-white/90 caret-white ring-offset-0 placeholder:text-white/30 hover:border-0 focus-visible:ring-0 focus-visible:ring-offset-0"
              defaultValue={actionData?.userData?.contents ?? EXAMPLE}
              spellCheck={false}
              required
            />
          </div>
          <FieldSetErrors />
        </FieldSet>

        <div className="order-1 flex flex-col gap-4 lg:sticky lg:top-20 lg:order-2">
          <Card className="flex flex-col gap-4 p-5">
            <FieldSet
              name="slug"
              errors={errors.slug}
              className="flex flex-col gap-1.5"
            >
              <FieldSetLabel>Stack slug</FieldSetLabel>
              <FieldSetInput
                className="font-mono"
                placeholder="ex: myapp"
                defaultValue={actionData?.userData?.slug}
                required
              />
              <FieldSetErrors />
            </FieldSet>

            {errors.non_field_errors && (
              <p className="text-sm text-destructive">
                {errors.non_field_errors}
              </p>
            )}

            <div className="flex flex-col gap-2 pt-1">
              <SubmitButton isPending={isPending} className="w-full gap-2">
                {isPending ? (
                  <>
                    <span>Creating…</span>
                    <LoaderIcon className="animate-spin" size={15} />
                  </>
                ) : (
                  "Create stack"
                )}
              </SubmitButton>
              <Link to={backHref} className="w-full">
                <Button variant="outline" className="w-full">
                  Cancel
                </Button>
              </Link>
            </div>
          </Card>
        </div>
      </Form>
    </section>
  );
}
