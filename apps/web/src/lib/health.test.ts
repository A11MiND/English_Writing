import { describe, expect, it } from "vitest";

import { readHealthStatus } from "./health";

describe("readHealthStatus", () => {
  it("returns ok state for successful health envelope", () => {
    const result = readHealthStatus({
      success: true,
      data: {
        service: "api",
        status: "ok",
        environment: "local",
        checks: { redis: "ok" },
      },
      request_id: "request-1",
    });

    expect(result.status).toBe("ok");
    expect(result.requestId).toBe("request-1");
  });

  it("returns error state for failed health envelope", () => {
    const result = readHealthStatus({
      success: false,
      error_code: "HEALTH_CHECK_FAILED",
      message: "Database health check failed.",
      request_id: "request-2",
    });

    expect(result).toEqual({
      status: "error",
      message: "Database health check failed.",
      requestId: "request-2",
    });
  });
});
