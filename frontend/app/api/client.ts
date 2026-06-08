import createClient, { type Middleware } from "openapi-fetch";
import { excerpt } from "~/utils";
import type { paths } from "./v1";

const throwErrorOnServerError: Middleware = {
  async onResponse({ response }) {
    if (response.status > 499) {
      let data: string;
      if (response.headers.get("content-type") === "application/json") {
        data = JSON.stringify(await response.json());
      } else {
        data = excerpt(await response.text(), 1000);
      }
      throw new Error(`Server Error from API: ${data}`);
    }
    return response;
  }
};

// Endpoints that answer 401 as a normal outcome — asking "am I logged in?"
// must not itself trigger a redirect, or the login page loops.
const AUTH_ENDPOINTS = [
  "/api/auth/login",
  "/api/auth/me",
  "/api/auth/check-user-existence",
  "/api/csrf"
];

const redirectToLoginOnUnauthorized: Middleware = {
  async onResponse({ request, response }) {
    if (response.status !== 401 || typeof window === "undefined") {
      return response;
    }
    const { pathname } = new URL(request.url);
    if (AUTH_ENDPOINTS.some((endpoint) => pathname.startsWith(endpoint))) {
      return response;
    }
    // The session died underneath a page that is already rendered. Without
    // this the dashboard stays up and every query fails with "error from API",
    // which reads as the backend being broken rather than a signed-out user.
    if (!window.location.pathname.startsWith("/login")) {
      const back = encodeURIComponent(
        window.location.pathname + window.location.search
      );
      window.location.assign(`/login?redirect_to=${back}`);
    }
    return response;
  }
};

const apiClient = createClient<paths>({
  baseUrl: "/"
});

apiClient.use(throwErrorOnServerError);
apiClient.use(redirectToLoginOnUnauthorized);

type RequestMethod = "post" | "put" | "get" | "delete" | "patch";

type ExtractRequestBody<
  TPaths,
  TPath extends keyof TPaths,
  TMethod extends RequestMethod
> = TPaths[TPath] extends Record<TMethod, infer TOperation>
  ? TOperation extends {
      requestBody?: { content: { "application/json": infer TRequestBody } };
    }
    ? TRequestBody
    : never
  : never;

type ExtractRequestParams<
  TPaths,
  TPath extends keyof TPaths,
  TMethod extends RequestMethod
> = TPaths[TPath] extends Record<TMethod, infer TOperation>
  ? TOperation extends {
      parameters?: { query: infer TRequestParams };
    }
    ? TRequestParams
    : never
  : never;

type PathsThatContainMethod<TPaths, TMethod extends RequestMethod> = {
  [K in keyof TPaths]: TPaths[K] extends Record<TMethod, unknown> ? K : never;
}[keyof TPaths];

export type RequestInput<
  TMethod extends RequestMethod,
  TPath extends PathsThatContainMethod<paths, TMethod>
> = ExtractRequestBody<paths, TPath, TMethod>;

export type RequestParams<
  TMethod extends RequestMethod,
  TPath extends PathsThatContainMethod<paths, TMethod>
> = ExtractRequestParams<paths, TPath, TMethod>;

type ExtractResponse<
  TPaths,
  TPath extends keyof TPaths,
  TMethod extends RequestMethod,
  TStatusCode extends number
> = TPaths[TPath] extends Record<TMethod, infer TOperation>
  ? TOperation extends {
      responses: Record<
        TStatusCode,
        { content: { "application/json": infer TResponseBody } }
      >;
    }
    ? TResponseBody
    : never
  : never;

export const HTTP_SUCCESS = 200;

export type ApiResponse<
  TMethod extends RequestMethod,
  TPath extends PathsThatContainMethod<paths, TMethod>,
  TStatusCode extends number = typeof HTTP_SUCCESS
> = ExtractResponse<paths, TPath, TMethod, TStatusCode>;

export { apiClient };
