import { afterEach, describe, expect, it, vi } from "vitest";
import { downloadBlob } from "./download";

describe("downloadBlob", () => {
  const originalCreate = URL.createObjectURL;
  const originalRevoke = URL.revokeObjectURL;

  afterEach(() => {
    URL.createObjectURL = originalCreate;
    URL.revokeObjectURL = originalRevoke;
    document.body.innerHTML = "";
    vi.restoreAllMocks();
  });

  it("creates object URL, triggers anchor click, and revokes URL", () => {
    const createUrl = vi.fn(() => "blob:mock-url");
    const revokeUrl = vi.fn();
    URL.createObjectURL = createUrl;
    URL.revokeObjectURL = revokeUrl;
    const clickSpy = vi.fn();
    const anchorProto = HTMLAnchorElement.prototype;
    const originalClick = anchorProto.click;
    anchorProto.click = clickSpy;

    try {
      downloadBlob(new Blob(["data"], { type: "application/octet-stream" }), "song.mid");
      expect(createUrl).toHaveBeenCalledTimes(1);
      expect(clickSpy).toHaveBeenCalledTimes(1);
      expect(revokeUrl).toHaveBeenCalledWith("blob:mock-url");
      // anchor 已被移除
      expect(document.querySelector("a")).not.toBeInTheDocument();
    } finally {
      anchorProto.click = originalClick;
    }
  });

  it("revokes URL even when anchor click throws", () => {
    const revokeUrl = vi.fn();
    URL.createObjectURL = vi.fn(() => "blob:mock-url");
    URL.revokeObjectURL = revokeUrl;
    const anchorProto = HTMLAnchorElement.prototype;
    const originalClick = anchorProto.click;
    anchorProto.click = () => {
      throw new Error("click blocked");
    };

    try {
      expect(() => downloadBlob(new Blob(["x"]), "a.wav")).toThrow("click blocked");
      expect(revokeUrl).toHaveBeenCalledWith("blob:mock-url");
    } finally {
      anchorProto.click = originalClick;
    }
  });
});
