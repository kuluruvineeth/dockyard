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
    route(
      "project/:projectSlug/:envSlug",
      "./routes/environments/environment-service-list.tsx"
    ),
    route(
      "project/:projectSlug/:envSlug/create-service/docker",
      "./routes/services/create-docker-service.tsx"
    )
  ])
] satisfies RouteConfig;
