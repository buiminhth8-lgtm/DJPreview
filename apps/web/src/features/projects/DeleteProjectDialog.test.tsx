import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { DeleteProjectDialog } from "./DeleteProjectDialog";
import type { ProjectSummary } from "./projectTypes";

const project: ProjectSummary = {
  songId: "song-123",
  title: "测试工程",
  createdAt: null,
  currentVersionId: "v1",
  hasMidi: false,
  hasAudio: false,
  hasStems: false,
  hasQualityReport: false,
  renderer: null,
  soundfontName: null,
};

describe("DeleteProjectDialog", () => {
  it("cancel does not call onConfirm", async () => {
    const onConfirm = vi.fn();
    const onCancel = vi.fn();
    render(
      <DeleteProjectDialog
        open
        project={project}
        isDeleting={false}
        onCancel={onCancel}
        onConfirm={onConfirm}
      />,
    );
    await userEvent.click(screen.getByRole("button", { name: "取消" }));
    expect(onConfirm).not.toHaveBeenCalled();
    expect(onCancel).toHaveBeenCalledTimes(1);
  });

  it("confirm calls onConfirm once", async () => {
    const onConfirm = vi.fn();
    render(
      <DeleteProjectDialog open project={project} isDeleting={false} onCancel={vi.fn()} onConfirm={onConfirm} />,
    );
    await userEvent.click(screen.getByRole("button", { name: "删除工程" }));
    expect(onConfirm).toHaveBeenCalledTimes(1);
  });

  it("isDeleting disables buttons and blocks duplicate submit", async () => {
    const onConfirm = vi.fn();
    render(
      <DeleteProjectDialog open project={project} isDeleting onCancel={vi.fn()} onConfirm={onConfirm} />,
    );
    const confirm = screen.getByRole("button", { name: "删除中…" });
    expect(confirm).toBeDisabled();
    expect(screen.getByRole("button", { name: "取消" })).toBeDisabled();
    // disabled 按钮不可点击，onConfirm 不会再次触发
    await userEvent.click(confirm).catch(() => undefined);
    expect(onConfirm).not.toHaveBeenCalled();
  });

  it("closed dialog renders nothing", () => {
    render(<DeleteProjectDialog open={false} project={project} isDeleting={false} onCancel={vi.fn()} onConfirm={vi.fn()} />);
    expect(screen.queryByText("删除工程？")).not.toBeInTheDocument();
  });
});
