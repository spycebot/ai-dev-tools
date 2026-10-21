import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { reply, stubFetch } from "../test/fetch";
import Login from "./Login";

describe("Login", () => {
  it("keeps Enter disabled until a password is typed", async () => {
    render(<Login onSuccess={vi.fn()} />);
    const enter = screen.getByRole("button", { name: "Enter" });
    expect(enter).toBeDisabled();
    await userEvent.type(screen.getByLabelText("Password"), "x");
    expect(enter).toBeEnabled();
  });

  it("calls onSuccess after a correct password", async () => {
    stubFetch({ "POST /api/login": reply(200, { authenticated: true }) });
    const onSuccess = vi.fn();
    render(<Login onSuccess={onSuccess} />);
    await userEvent.type(screen.getByLabelText("Password"), "right password{Enter}");
    await vi.waitFor(() => expect(onSuccess).toHaveBeenCalledOnce());
  });

  it("shows the server's error and clears the field after a wrong password", async () => {
    stubFetch({ "POST /api/login": reply(401, { detail: "Incorrect password" }) });
    const onSuccess = vi.fn();
    render(<Login onSuccess={onSuccess} />);
    await userEvent.type(screen.getByLabelText("Password"), "wrong{Enter}");
    expect(await screen.findByText("Incorrect password")).toBeInTheDocument();
    expect(screen.getByLabelText("Password")).toHaveValue("");
    expect(onSuccess).not.toHaveBeenCalled();
  });

  it("shows a message passed in by the app (e.g. an expired session)", () => {
    render(<Login message="Your session expired. Please log in again." onSuccess={vi.fn()} />);
    expect(screen.getByText("Your session expired. Please log in again.")).toBeInTheDocument();
  });
});
