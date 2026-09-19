import { describe, expect, it } from "vitest";

import { normalizeSystemAdminWorkspaceNavigation } from "./AppShell";

describe("SYSTEM_ADMIN workspace navigation normalization", () => {
  it.each(["admin-monitoring", "admin-audit"])(
    "normalizes retired active menu %s to dashboard",
    (activeMenu) => {
      expect(
        normalizeSystemAdminWorkspaceNavigation(activeMenu, [
          "admin-users",
          activeMenu,
          "admin-settings",
        ]),
      ).toEqual({
        activeMenu: "dashboard",
        openMenuTabs: ["admin-users", "admin-settings"],
      });
    },
  );

  it("removes retired tabs while preserving the current dashboard", () => {
    expect(
      normalizeSystemAdminWorkspaceNavigation("dashboard", [
        "admin-monitoring",
        "admin-users",
        "admin-audit",
      ]),
    ).toEqual({
      activeMenu: "dashboard",
      openMenuTabs: ["admin-users"],
    });
  });
});
