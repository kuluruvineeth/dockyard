import * as React from "react";
import { Checkbox } from "~/components/ui/checkbox";
import { Input } from "~/components/ui/input";
import { PasswordToggleInput } from "~/components/ui/password-toggle-input";
import { Textarea } from "~/components/ui/textarea";

import { cn } from "~/lib/utils";

export type FieldSetProps = {
  errors?: string | string[];
  children: React.ReactNode;
  required?: boolean;
} & React.ComponentProps<"fieldset">;

type FieldSetContextValue = {
  id: string;
  name?: string;
  errors?: string | string[];
  required?: boolean;
};

const FieldSetContext = React.createContext<FieldSetContextValue | null>(null);

export function FieldSet({
  className,
  errors,
  children,
  name,
  required,
  ...props
}: FieldSetProps) {
  const id = React.useId();
  const childrenArray = React.Children.toArray(children);

  const isErrorComponentInChildren = childrenArray.some(
    (child) =>
      typeof child === "object" &&
      child !== null &&
      React.isValidElement(child) &&
      child.type === FieldSetErrors
  );

  return (
    <FieldSetContext value={{ id, errors, name, required }}>
      <fieldset className={className} {...props}>
        {children}
        {!isErrorComponentInChildren && errors && <FieldSetErrors />}
      </fieldset>
    </FieldSetContext>
  );
}

export function FieldSetErrors(
  props: Omit<React.ComponentProps<"span">, "id">
) {
  const ctx = React.use(FieldSetContext);
  if (!ctx) {
    throw new Error(
      "<FieldSetErrors> component should be inside of a <FieldSet> component"
    );
  }
  const { id, errors } = ctx;
  return (
    <span
      id={`${id}-error`}
      aria-live="assertive"
      className={cn("text-red-500 text-sm", props.className)}
    >
      {errors &&
        (typeof errors === "string"
          ? errors
          : errors.map((err) => (
              <React.Fragment key={err}>
                {err}
                <br />
              </React.Fragment>
            )))}
    </span>
  );
}

export function FieldSetLabel(props: React.ComponentProps<"label">) {
  const ctx = React.use(FieldSetContext);
  if (!ctx) {
    throw new Error(
      "<FieldSetLabel> component should be inside of a <FieldSet> component"
    );
  }

  const { id } = ctx;
  return (
    <label
      htmlFor={props.htmlFor ?? id}
      {...props}
      className={cn("dark:text-gray-400", props.className)}
    >
      {props.children}
      {ctx.required && (
        <>
          <span aria-hidden className="text-amber-600 dark:text-yellow-500">
            &nbsp;*
          </span>
          <span className="sr-only">(required)</span>
        </>
      )}
    </label>
  );
}

export function FieldSetInput(
  props: Omit<
    React.ComponentProps<typeof Input>,
    "id" | "aria-invalid" | "aria-describedby"
  >
) {
  const ctx = React.use(FieldSetContext);
  if (!ctx) {
    throw new Error(
      "<FieldSetInput> component should be inside of a <FieldSet> component"
    );
  }

  const { id, errors, name } = ctx;
  return (
    <Input
      id={id}
      aria-invalid={Boolean(errors)}
      aria-describedby={`${id}-error`}
      {...props}
      name={props.name ?? name}
    />
  );
}

export function FieldSetPasswordToggleInput(
  props: Omit<
    React.ComponentProps<typeof PasswordToggleInput>,
    "id" | "aria-invalid" | "aria-describedby"
  >
) {
  const ctx = React.use(FieldSetContext);
  if (!ctx) {
    throw new Error(
      "<FieldSetInput> component should be inside of a <FieldSet> component"
    );
  }

  const { id, errors, name } = ctx;
  return (
    <PasswordToggleInput
      id={id}
      aria-invalid={Boolean(errors)}
      aria-describedby={`${id}-error`}
      {...props}
      name={props.name ?? name}
    />
  );
}

export function FieldSetTextarea(
  props: Omit<
    React.ComponentProps<typeof Textarea>,
    "id" | "aria-invalid" | "aria-describedby"
  >
) {
  const ctx = React.use(FieldSetContext);
  if (!ctx) {
    throw new Error(
      "<FieldSetTextarea> component should be inside of a <FieldSet> component"
    );
  }

  const { id, errors, name } = ctx;
  return (
    <Textarea
      id={id}
      aria-invalid={Boolean(errors)}
      aria-describedby={`${id}-error`}
      {...props}
      name={props.name ?? name}
    />
  );
}

export function FieldSetCheckbox(
  props: Omit<
    React.ComponentProps<typeof Checkbox>,
    "id" | "aria-invalid" | "aria-describedby"
  >
) {
  const ctx = React.use(FieldSetContext);
  if (!ctx) {
    throw new Error(
      "<FieldSetCheckbox> component should be inside of a <FieldSet> component"
    );
  }

  const { id, errors, name } = ctx;
  return (
    <Checkbox
      id={id}
      aria-invalid={Boolean(errors)}
      aria-describedby={`${id}-error`}
      {...props}
      name={props.name ?? name}
    />
  );
}
