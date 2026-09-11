import { Navigate, Outlet } from "react-router-dom";
import { getSession, hasOnboarded } from "../lib/auth";

export function RequireAuth() {
  if (!hasOnboarded()) return <Navigate to="/splash" replace />;
  if (!getSession()) return <Navigate to="/login" replace />;
  return <Outlet />;
}
