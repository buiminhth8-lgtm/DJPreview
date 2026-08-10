import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { TimelineHeader } from "./TimelineHeader";

describe("TimelineHeader transport geometry", () => {
  it("click-to-seek maps the same zoomed x geometry back to tick", () => {
    const onSeek = vi.fn();
    const { rerender } = render(
      <TimelineHeader
        ppq={480}
        meter={{ numerator: 4, denominator: 4 }}
        maxTick={7680}
        pixelsPerTick={0.4}
        currentTick={480}
        onSeek={onSeek}
      />,
    );
    const timeline = screen.getByRole("slider", { name: /MIDI 时间轴/ });
    vi.spyOn(timeline, "getBoundingClientRect").mockReturnValue({
      left: 100,
      top: 0,
      right: 3172,
      bottom: 28,
      width: 3072,
      height: 28,
      x: 100,
      y: 0,
      toJSON: () => ({}),
    });
    fireEvent.click(timeline, { clientX: 292 });
    expect(onSeek).toHaveBeenCalledWith(480);
    expect(screen.getByTestId("timeline-playhead")).toHaveStyle({ left: "192px" });

    rerender(
      <TimelineHeader
        ppq={480}
        meter={{ numerator: 4, denominator: 4 }}
        maxTick={7680}
        pixelsPerTick={0.8}
        currentTick={480}
        onSeek={onSeek}
      />,
    );
    expect(screen.getByTestId("timeline-playhead")).toHaveStyle({ left: "384px" });
  });

  it("renders a validated loop region from canonical ticks", () => {
    render(
      <TimelineHeader
        ppq={480}
        meter={{ numerator: 4, denominator: 4 }}
        maxTick={7680}
        pixelsPerTick={0.5}
        loopEnabled
        loopStartTick={1920}
        loopEndTick={3840}
      />,
    );
    expect(screen.getByTestId("timeline-loop-region")).toHaveStyle({ left: "960px", width: "960px" });
  });
});
