import { AlertCircle, CheckIcon, LoaderIcon } from "lucide-react";
import * as React from "react";
import { Form, redirect, useNavigation } from "react-router";
import { toast } from "sonner";
import { apiClient } from "~/api/client";
import { DockyardLogo } from "~/components/logo";
import { Alert, AlertDescription, AlertTitle } from "~/components/ui/alert";
import { SubmitButton } from "~/components/ui/button";
import { Input } from "~/components/ui/input";
import { userQueries } from "~/lib/queries";
import {
  type ErrorResponseFromAPI,
  cn,
  getFormErrorsFromResponseData
} from "~/lib/utils";
import { queryClient } from "~/root";
import { getCsrfTokenHeader, metaTitle } from "~/utils";
import type { Route } from "./+types/onboarding";

export const meta: Route.MetaFunction = () => [
  metaTitle("Welcome to Dockyard")
];

const COMMON_PASSWORDS = new Set([
  "password",
  "password1",
  "12345678",
  "123456789",
  "qwerty",
  "qwertyuiop",
  "letmein",
  "admin",
  "welcome",
  "iloveyou",
  "dockyard"
]);

export async function clientLoader() {
  const userExist = await queryClient.ensureQueryData(
    userQueries.checkUserExistence
  );

  if (userExist?.exists) {
    throw redirect("/login");
  }
  return;
}

export async function clientAction({ request }: Route.ClientActionArgs) {
  const formData = await request.formData();

  const credentials = {
    username: formData.get("username")!.toString(),
    password: formData.get("password")!.toString(),
    password_confirmation: formData.get("password_confirmation")!.toString()
  };

  if (credentials.password !== credentials.password_confirmation) {
    return {
      errors: {
        type: "validation_error",
        errors: [
          {
            attr: "password",
            detail: "Your passwords do not match",
            code: "validation_error"
          },
          {
            attr: "password_confirmation",
            detail: "Your passwords do not match",
            code: "validation_error"
          }
        ]
      } satisfies ErrorResponseFromAPI,
      userData: credentials
    };
  }

  const { error: errors, data } = await apiClient.POST(
    "/api/auth/create-initial-user",
    {
      headers: { ...(await getCsrfTokenHeader()) },
      body: {
        username: credentials.username,
        password: credentials.password
      }
    }
  );
  if (errors) {
    return { errors, userData: credentials };
  }

  queryClient.removeQueries(userQueries.checkUserExistence);
  queryClient.removeQueries(userQueries.authedUser);

  toast.success("Success", {
    description: data.detail,
    closeButton: true
  });

  throw redirect("/");
}

export default function InitialRegistration({
  actionData
}: Route.ComponentProps) {
  const navigation = useNavigation();

  const isPending =
    navigation.state === "loading" || navigation.state === "submitting";
  const formRef = React.useRef<React.ComponentRef<"form">>(null);

  const errors = getFormErrorsFromResponseData(actionData?.errors);

  const [password, setPassword] = React.useState(
    actionData?.userData?.password ?? ""
  );
  const passwordRules = [
    {
      label: "Mix of upper, lower, numbers, and symbols",
      passed:
        /[a-z]/.test(password) &&
        /[A-Z]/.test(password) &&
        /[0-9]/.test(password) &&
        /[^A-Za-z0-9]/.test(password)
    },
    {
      label: "Not a common password",
      passed:
        password.length > 0 && !COMMON_PASSWORDS.has(password.toLowerCase())
    },
    {
      label: "At least 12 characters long",
      passed: password.length >= 12
    }
  ];

  React.useEffect(() => {
    if (navigation.state === "idle" && actionData?.errors) {
      const fieldErrors = getFormErrorsFromResponseData(actionData?.errors);
      const key = Object.keys(fieldErrors ?? {})[0];
      const field = formRef.current?.elements.namedItem(
        key
      ) as HTMLInputElement;
      field?.focus();
    }
  }, [navigation.state, actionData]);

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
      <div className="relative flex w-full max-w-md flex-col items-center gap-8">
        <div className="flex flex-col items-center gap-2 text-center">
          <h1 className="text-3xl font-bold tracking-tighter">
            Create the first user
          </h1>
          <p className="text-sm text-grey text-balance">
            Let's set up your first user to get started.
          </p>
        </div>

        <Form
          method="POST"
          ref={formRef}
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

            <div className="flex flex-col gap-1.5">
              <label htmlFor="username" className="text-sm font-medium">
                Username
              </label>
              <Input
                id="username"
                name="username"
                placeholder="ex: JohnDoe"
                defaultValue={actionData?.userData?.username}
                type="text"
                aria-describedby="username-error"
                aria-invalid={!!errors.username}
              />
              {errors.username && (
                <span id="username-error" className="text-sm text-destructive">
                  {errors.username}
                </span>
              )}
            </div>

            <div className="flex flex-col gap-1.5">
              <label htmlFor="password" className="text-sm font-medium">
                Password
              </label>
              <Input
                type="password"
                name="password"
                id="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                aria-invalid={!!errors.password}
                aria-describedby="password-error"
              />
              {errors.password && (
                <span id="password-error" className="text-sm text-destructive">
                  {errors.password}
                </span>
              )}
            </div>

            <div className="flex flex-col gap-1.5">
              <label
                htmlFor="password_confirmation"
                className="text-sm font-medium"
              >
                Confirm your password
              </label>
              <Input
                type="password"
                name="password_confirmation"
                id="password_confirmation"
                defaultValue={actionData?.userData?.password_confirmation}
                aria-invalid={!!errors.password_confirmation}
                aria-describedby="password_confirmation-error"
              />
              {errors.password_confirmation && (
                <span
                  id="password_confirmation-error"
                  className="text-sm text-destructive"
                >
                  {errors.password_confirmation}
                </span>
              )}
            </div>

            <div className="flex flex-col gap-2.5 border border-border bg-foreground/[0.015] p-3.5">
              <h3 className="text-[11px] font-medium uppercase tracking-[0.16em] text-grey">
                Hints for a good password
              </h3>
              <ul className="flex list-none flex-col gap-1.5 text-xs">
                {passwordRules.map((rule) => (
                  <li
                    key={rule.label}
                    className={cn(
                      "flex items-center gap-2 transition-colors duration-200",
                      rule.passed ? "text-foreground" : "text-grey"
                    )}
                  >
                    <CheckIcon
                      size={13}
                      strokeWidth={2.5}
                      className={cn(
                        "flex-none transition-opacity duration-200",
                        rule.passed ? "opacity-100" : "opacity-25"
                      )}
                    />
                    {rule.label}
                  </li>
                ))}
              </ul>
            </div>

            <SubmitButton className="mt-2 w-full gap-2" isPending={isPending}>
              {isPending ? (
                <>
                  <span>Creating...</span>
                  <LoaderIcon className="animate-spin" size={15} />
                </>
              ) : (
                "Create your first user"
              )}
            </SubmitButton>
          </div>
        </Form>
      </div>

      <p className="pointer-events-none absolute bottom-6 left-1/2 -translate-x-1/2 font-mono text-[11px] tracking-tight text-grey">
        Dockyard · self-hosted PaaS
      </p>
    </main>
  );
}
