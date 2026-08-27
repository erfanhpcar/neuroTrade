import { describe, expect, it } from "vitest";

import { backendOrigin } from "@/lib/backend";

describe("backendOrigin", () => {
  it("defaults to loopback for native next dev", () => {
    const previous = process.env.BACKEND_URL;
    delete process.env.BACKEND_URL;
    try {
      expect(backendOrigin()).toBe("http://127.0.0.1:8000");
    } finally {
      if (previous === undefined) {
        delete process.env.BACKEND_URL;
      } else {
        process.env.BACKEND_URL = previous;
      }
    }
  });

  it("strips a trailing slash from BACKEND_URL", () => {
    const previous = process.env.BACKEND_URL;
    process.env.BACKEND_URL = "http://backend:8000/";
    try {
      expect(backendOrigin()).toBe("http://backend:8000");
    } finally {
      if (previous === undefined) {
        delete process.env.BACKEND_URL;
      } else {
        process.env.BACKEND_URL = previous;
      }
    }
  });
});
