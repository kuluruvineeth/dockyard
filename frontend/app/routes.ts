import { type RouteConfig, index, route } from "@react-router/dev/routes";

export default [
  route("onboarding", "./routes/onboarding.tsx"),
  index("./routes/home.tsx")
] satisfies RouteConfig;
