import { useEffect } from "react";
import { useProjectInfoStore } from "./projectInfoStore";

export function useProjectInfoReady(): boolean {
  const status = useProjectInfoStore((state) => state.status);
  const ensureLoaded = useProjectInfoStore((state) => state.ensureLoaded);

  useEffect(() => {
    ensureLoaded().catch(console.error);
  }, [ensureLoaded]);

  return status === "ready";
}

export function ProjectInfoBootstrapper(): null {
  useProjectInfoReady();
  return null;
}
