import { type RouteConfig, index, route } from "@react-router/dev/routes";

export default [
  route("login", "./routes/login.tsx"),
  route("logout", "./routes/logout.tsx"),
  route("onboarding", "./routes/onboarding.tsx"),
  index("./routes/home.tsx")
] satisfies RouteConfig;
