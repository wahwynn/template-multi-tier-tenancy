import { describe, it, expect } from "vitest";
import { routing } from "@/i18n/routing";

describe("i18n routing", () => {
  it("defaults to English locale", () => {
    expect(routing.defaultLocale).toBe("en");
  });

  it("uses as-needed prefix so English URLs have no locale segment", () => {
    expect(routing.localePrefix).toBe("as-needed");
  });

  it("includes English in supported locales", () => {
    expect(routing.locales).toContain("en");
  });
});
