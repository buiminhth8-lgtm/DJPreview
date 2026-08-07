import { describe, expect, it, vi, beforeEach } from "vitest";
import { act, renderHook, waitFor } from "@testing-library/react";
import { useProject } from "./useProject";
import * as projectApi from "./projectApi";

vi.mock("./projectApi", () => ({
  getProject: vi.fn(),
}));

function deferred<T>() {
  let resolve!: (v: T) => void;
  let reject!: (e: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

describe("useProject songId isolation", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("old song request result cannot overwrite new song state", async () => {
    const first = deferred<{ songId: string; title: string; musicSpec: unknown }>();
    const second = deferred<{ songId: string; title: string; musicSpec: unknown }>();
    (projectApi.getProject as ReturnType<typeof vi.fn>)
      .mockImplementationOnce(() => first.promise)
      .mockImplementationOnce(() => second.promise);

    const { result, rerender } = renderHook(({ id }) => useProject(id), { initialProps: { id: "songA" } });
    // songA 请求挂起
    await waitFor(() => expect(projectApi.getProject).toHaveBeenCalledTimes(1));

    // 切换到 songB → 旧请求被 abort（AbortController.signal.aborted 后结果被忽略）
    rerender({ id: "songB" });
    await waitFor(() => expect(projectApi.getProject).toHaveBeenCalledTimes(2));

    // 旧请求晚返回（即使 resolve，controller 已 aborted → state 不更新）
    await act(() => first.resolve({ songId: "songA", title: "A", musicSpec: {} }));
    expect(result.current.project?.songId).not.toBe("songA");

    await act(() => second.resolve({ songId: "songB", title: "B", musicSpec: {} }));
    await waitFor(() => expect(result.current.project?.songId).toBe("songB"));
  });
});
