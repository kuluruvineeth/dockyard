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
  layout("./routes/dashboard-layout.tsx", [index("./routes/home.tsx")])
] satisfies RouteConfig;
