import {
  type RouteConfig,
  index,
  layout,
  route
} from "@react-router/dev/routes";

export default [
  route("login", "./routes/login.tsx"),
  route("logout", "./routes/logout.tsx"),
  route("onboarding", "./routes/onboarding.tsx"),
  layout("./routes/dashboard-layout.tsx", [
    index("./routes/home.tsx"),
    route("create-project", "./routes/projects/create-project.tsx"),
    route("settings", "./routes/settings/registry-credentials.tsx"),
    route("settings/git-apps", "./routes/settings/git-apps.tsx"),
    route("settings/ssh-keys", "./routes/settings/ssh-keys.tsx"),
    route(
      "project/:projectSlug/:envSlug",
      "./routes/environments/environment-service-list.tsx"
    ),
    route(
      "project/:projectSlug/:envSlug/create-service/docker",
      "./routes/services/create-docker-service.tsx"
    ),
    route(
      "project/:projectSlug/:envSlug/create-service/git",
      "./routes/services/create-git-service.tsx"
    ),
    route(
      "project/:projectSlug/:envSlug/create-compose-stack",
      "./routes/services/create-compose-stack.tsx"
    ),
    route(
      "project/:projectSlug/:envSlug/services/:slug",
      "./routes/services/service-detail.tsx"
    )
  ])
] satisfies RouteConfig;
