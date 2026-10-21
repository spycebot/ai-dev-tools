// Vitest setup: jest-dom matchers (toBeInTheDocument, ...) and a clean DOM,
// stubs and mocks after every test.
import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach, vi } from "vitest";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
  vi.useRealTimers();
});
