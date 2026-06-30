import { describe, expect, it } from "vitest";

import { routeForRole } from "./auth";

describe("routeForRole", () => {
  it("routes students to student home", () => {
    expect(routeForRole("STUDENT")).toBe("/student");
  });

  it("routes teachers to teacher dashboard", () => {
    expect(routeForRole("TEACHER")).toBe("/teacher");
  });

  it("routes admins to admin console", () => {
    expect(routeForRole("SCHOOL_ADMIN")).toBe("/admin");
    expect(routeForRole("SYSTEM_ADMIN")).toBe("/admin");
  });

  it("routes unknown privileged roles to admin console", () => {
    expect(routeForRole("SYSTEM_ADMIN")).toBe("/admin");
  });
});
