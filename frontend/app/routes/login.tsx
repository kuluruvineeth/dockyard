import { AlertCircle, LoaderIcon } from "lucide-react";
import { Form, redirect, useNavigation } from "react-router";
import { apiClient } from "~/api/client";
import { DockyardLogo } from "~/components/logo";
import { Alert, AlertDescription, AlertTitle } from "~/components/ui/alert";
import { SubmitButton } from "~/components/ui/button";
import {
  FieldSet,
  FieldSetInput,
  FieldSetLabel,
  FieldSetPasswordToggleInput
} from "~/components/ui/fieldset";
import { userQueries } from "~/lib/queries";
import { getFormErrorsFromResponseData } from "~/lib/utils";
import { queryClient } from "~/root";
import { getCsrfTokenHeader, metaTitle } from "~/utils";
import type { Route } from "./+types/login";

export const meta: Route.MetaFunction = () => [metaTitle("Login")];

export async function clientLoader({ request }: Route.ClientLoaderArgs) {
  const [user, userExist] = await Promise.all([
    queryClient.ensureQueryData(userQueries.authedUser),
    queryClient.ensureQueryData(userQueries.checkUserExistence)
  ]);

  if (!userExist?.exists) {
    throw redirect("/onboarding");
  }

  const searchParams = new URL(request.url).searchParams;

  if (user) {
    const redirect_to = searchParams.get("redirect_to");
    let redirectTo = "/";
    if (redirect_to && URL.canParse(redirect_to, window.location.href)) {
      redirectTo = redirect_to;
    }
    throw redirect(redirectTo);
  }
  return;
}

export async function clientAction({ request }: Route.ClientActionArgs) {
  const formData = await request.formData();
  const searchParams = new URL(request.url).searchParams;

  const credentials = {
    username: formData.get("username")?.toString() ?? "",
    password: formData.get("password")?.toString() ?? ""
  };

  const { error: errors, data } = await apiClient.POST("/api/auth/login", {
    headers: { ...(await getCsrfTokenHeader()) },
    body: credentials
  });
  if (errors) {
    return { errors, userData: credentials };
  }
  if (data?.success) {
    queryClient.removeQueries(userQueries.authedUser);

    const redirect_to = searchParams.get("redirect_to");
    let redirectTo = "/";
    if (redirect_to && URL.canParse(redirect_to, window.location.href)) {
      redirectTo = redirect_to;
    }
    throw redirect(redirectTo);
  }
}

export default function LoginPage({ actionData }: Route.ComponentProps) {
  const navigation = useNavigation();
  const isPending =
    navigation.state === "loading" || navigation.state === "submitting";
  const errors = getFormErrorsFromResponseData(actionData?.errors);
  return (
    <main className="relative flex min-h-[100dvh] flex-col items-center justify-center overflow-hidden px-6 py-12">
      <DockyardLogo
        aria-hidden
        className="pointer-events-none absolute -bottom-24 -right-24 size-[40rem] select-none text-foreground/[0.03]"
      />
      <div className="pointer-events-none absolute left-6 top-6 flex items-center gap-2.5">
        <DockyardLogo className="size-7 text-foreground" />
        <span className="font-bold tracking-tight">Dockyard</span>
      </div>
      <div className="relative flex w-full max-w-sm flex-col items-center gap-8">
        <div className="flex flex-col items-center gap-2 text-center">
          <h1 className="text-3xl font-bold tracking-tighter">
            Log in to Dockyard
          </h1>
          <p className="text-sm text-grey text-balance">
            Welcome back. Enter your credentials to continue.
          </p>
        </div>

        <Form
          method="POST"
          className="w-full border border-border bg-card text-card-foreground shadow-[0_1px_2px_hsl(var(--foreground)/0.04)] p-7 sm:p-8"
        >
          <div className="flex flex-col gap-4">
            {errors.non_field_errors && (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertTitle>Error</AlertTitle>
                <AlertDescription>{errors.non_field_errors}</AlertDescription>
              </Alert>
            )}

            <FieldSet
              errors={errors.username}
              name="username"
              className="flex flex-col gap-1.5"
            >
              <FieldSetLabel>Username</FieldSetLabel>
              <FieldSetInput
                placeholder="ex: JohnDoe"
                defaultValue={actionData?.userData?.username}
              />
            </FieldSet>

            <FieldSet
              name="password"
              errors={errors.password}
              className="flex flex-col gap-1.5"
            >
              <FieldSetLabel>Password</FieldSetLabel>
              <FieldSetPasswordToggleInput
                defaultValue={actionData?.userData?.password}
              />
            </FieldSet>

            <SubmitButton className="mt-2 w-full gap-2" isPending={isPending}>
              {isPending ? (
                <>
                  <span>Submitting...</span>
                  <LoaderIcon className="animate-spin" size={15} />
                </>
              ) : (
                "Log in"
              )}
            </SubmitButton>
          </div>
        </Form>

        <p className="text-xs text-grey">
          Trouble logging in? Contact your Dockyard administrator.
        </p>
      </div>

      <p className="pointer-events-none absolute bottom-6 left-1/2 -translate-x-1/2 font-mono text-[11px] tracking-tight text-grey">
        Dockyard · self-hosted PaaS
      </p>
    </main>
  );
}
