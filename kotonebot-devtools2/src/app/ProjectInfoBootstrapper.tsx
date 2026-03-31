import { useEffect } from "react";
import { useProjectInfoStore } from "./projectInfoStore";

export function ProjectInfoBootstrapper(): null {
  const ensureLoaded = useProjectInfoStore((state) => state.ensureLoaded);

  useEffect(() => {
    ensureLoaded().catch(console.error);
  }, [ensureLoaded]);

  return null;
}
