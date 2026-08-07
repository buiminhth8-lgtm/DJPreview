import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { RendererStatusCard } from "./RendererStatusCard";
import type { AudioRenderMetadata } from "../../api/types";

function meta(overrides: Partial<AudioRenderMetadata>): AudioRenderMetadata {
  return {
    renderer: "fluidsynth",
    isFallback: false,
    fallbackReason: null,
    soundfontName: "GeneralUser-GS",
    ...overrides,
  };
}

describe("RendererStatusCard fallback semantics", () => {
  it("isFallback=true shows fallback warning with reason", () => {
    render(
      <RendererStatusCard
        metadata={meta({ isFallback: true, fallbackReason: "fluidsynth_unavailable", renderer: "fallback" })}
      />,
    );
    expect(screen.getByText(/当前为预览级音色（fallback）/)).toBeInTheDocument();
    expect(screen.getByText(/FluidSynth 不可用/)).toBeInTheDocument();
  });

  it("isFallback=false + fluidsynth shows FluidSynth and no fallback warning", () => {
    render(
      <RendererStatusCard
        metadata={meta({ renderer: "fluidsynth", isFallback: false, soundfontName: "GeneralUser-GS" })}
      />,
    );
    expect(screen.queryByText(/当前为预览级音色（fallback）/)).not.toBeInTheDocument();
    expect(screen.getByText(/已使用采样音源/)).toBeInTheDocument();
    expect(screen.getByText("GeneralUser-GS")).toBeInTheDocument();
  });

  it("no WAV / no metadata renders not-rendered state, not fallback", () => {
    render(<RendererStatusCard metadata={null} />);
    expect(screen.getByText(/暂无渲染器信息/)).toBeInTheDocument();
    expect(screen.queryByText(/当前为预览级音色（fallback）/)).not.toBeInTheDocument();
  });

  it("never infers fallback from renderer name alone", () => {
    // renderer=fallback 但 isFallback 未显式 true → 不显示 fallback warning
    render(<RendererStatusCard metadata={meta({ renderer: "fallback", isFallback: false })} />);
    expect(screen.queryByText(/当前为预览级音色（fallback）/)).not.toBeInTheDocument();
  });
});
