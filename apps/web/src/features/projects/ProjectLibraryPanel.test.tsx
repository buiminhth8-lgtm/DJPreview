import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { ProjectLibraryPanel } from "./ProjectLibraryPanel";
import type { ProjectSummary } from "./projectTypes";

function project(id: string, title: string): ProjectSummary {
  return {
    songId: id,
    title,
    createdAt: null,
    currentVersionId: "v1",
    hasMidi: false,
    hasAudio: false,
    hasStems: false,
    hasQualityReport: false,
    renderer: null,
    soundfontName: null,
  };
}

const projects = [project("aaa", "Alpha"), project("bbb", "Beta"), project("ccc", "Gamma")];

function renderPanel(props: Record<string, unknown> = {}) {
  return render(
    <MemoryRouter>
      <ProjectLibraryPanel
        projects={projects}
        onDelete={vi.fn()}
        onRefresh={vi.fn()}
        selectedIds={new Set()}
        onToggleSelect={vi.fn()}
        onSelectAll={vi.fn()}
        onClearSelection={vi.fn()}
        onBatchDelete={vi.fn()}
        {...props}
      />
    </MemoryRouter>,
  );
}

describe("ProjectLibraryPanel selection", () => {
  it("renders checkboxes with accessible labels", () => {
    renderPanel();
    expect(screen.getByLabelText("选择工程 Alpha")).toBeInTheDocument();
    expect(screen.getByLabelText("选择工程 Beta")).toBeInTheDocument();
    expect(screen.getByLabelText("选择工程 Gamma")).toBeInTheDocument();
  });

  it("shows selected count and batch action only when something is selected", () => {
    const { rerender } = renderPanel({ selectedIds: new Set(["aaa"]) });
    expect(screen.getByText(/已选择 1 个工程/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "删除所选工程" })).toBeInTheDocument();

    rerender(
      <MemoryRouter>
        <ProjectLibraryPanel
          projects={projects}
          onDelete={vi.fn()}
          onRefresh={vi.fn()}
          selectedIds={new Set()}
          onToggleSelect={vi.fn()}
          onSelectAll={vi.fn()}
          onClearSelection={vi.fn()}
          onBatchDelete={vi.fn()}
        />
      </MemoryRouter>,
    );
    expect(screen.queryByText(/已选择/)).not.toBeInTheDocument();
  });

  it("toggle select calls onToggleSelect with songId", async () => {
    const onToggleSelect = vi.fn();
    renderPanel({ onToggleSelect });
    await userEvent.click(screen.getByLabelText("选择工程 Alpha"));
    expect(onToggleSelect).toHaveBeenCalledWith("aaa");
  });

  it("select all current results calls onSelectAll with visible ids", async () => {
    const onSelectAll = vi.fn();
    renderPanel({ onSelectAll });
    await userEvent.click(screen.getByLabelText("全选当前筛选结果"));
    expect(onSelectAll).toHaveBeenCalledWith(["aaa", "bbb", "ccc"]);
  });

  it("checkbox click does not navigate (no anchor/button navigation triggered)", async () => {
    const onToggleSelect = vi.fn();
    renderPanel({ onToggleSelect });
    const checkbox = screen.getByLabelText("选择工程 Beta");
    await userEvent.click(checkbox);
    expect(onToggleSelect).toHaveBeenCalledTimes(1);
  });
});
