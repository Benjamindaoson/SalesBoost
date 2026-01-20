import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, act, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { VirtuosoMockContext } from "react-virtuoso";
import { PracticeRoom } from "./PracticeRoom";

let mockReadyState = 1;
let latestOptions: any;
const sendJsonMessage = vi.fn();

vi.mock("react-use-websocket", () => {
  return {
    __esModule: true,
    default: (_url: string, options: any) => {
      latestOptions = options;
      return { sendJsonMessage, readyState: mockReadyState };
    },
    ReadyState: {
      CONNECTING: 0,
      OPEN: 1,
      CLOSING: 2,
      CLOSED: 3,
      UNINSTANTIATED: -1,
    },
  };
});

function renderRoom() {
  return render(
    <VirtuosoMockContext.Provider value={{ viewportHeight: 800, itemHeight: 72 }}>
      <div style={{ height: 900 }}>
        <PracticeRoom
          sessionId="test-session"
          initialNPCDetails={{ avatar: "/favicon.svg", tags: ["高需求客户", "异议处理", "场景对练"] }}
        />
      </div>
    </VirtuosoMockContext.Provider>
  );
}

describe("PracticeRoom", () => {
  beforeEach(() => {
    sendJsonMessage.mockClear();
    latestOptions = undefined;
    mockReadyState = 1;
  });

  afterEach(() => {
    vi.useRealTimers();
    cleanup();
  });

  it("renders connection status indicator", () => {
    mockReadyState = 0;
    const view = renderRoom();
    expect(screen.getByText("连接中")).toBeInTheDocument();

    mockReadyState = 1;
    view.rerender(
      <VirtuosoMockContext.Provider value={{ viewportHeight: 800, itemHeight: 72 }}>
        <div style={{ height: 900 }}>
          <PracticeRoom
            sessionId="test-session"
            initialNPCDetails={{ avatar: "/favicon.svg", tags: ["高需求客户", "异议处理", "场景对练"] }}
          />
        </div>
      </VirtuosoMockContext.Provider>
    );
    expect(screen.getByText("已连接")).toBeInTheDocument();
  });

  it("sends text message with required payload format", async () => {
    const user = userEvent.setup();
    renderRoom();

    const input = screen.getByPlaceholderText("输入你的话术，Shift+Enter 换行…");
    await user.type(input, "你好客户");
    await user.click(screen.getByRole("button", { name: "发送" }));

    expect(sendJsonMessage).toHaveBeenCalledTimes(1);
    expect(sendJsonMessage).toHaveBeenCalledWith(
      expect.objectContaining({ type: "text", content: "你好客户", timestamp: expect.any(Number) })
    );
  });

  it("receives npc and coach messages and throttles rendering", async () => {
    vi.useFakeTimers();
    renderRoom();

    act(() => {
      latestOptions?.onMessage?.({
        data: JSON.stringify({ role: "npc", content: "您好，我想了解一下。" }),
      });
      latestOptions?.onMessage?.({
        data: JSON.stringify({
          role: "coach",
          type: "coach_hint",
          level: "suggestion",
          title: "建议",
          content: "先确认客户需求，再给出方案。",
        }),
      });
    });

    act(() => {
      vi.advanceTimersByTime(100);
    });
    expect(screen.getByText("您好，我想了解一下。")).toBeInTheDocument();

    act(() => {
      vi.advanceTimersByTime(100);
    });
    expect(screen.getByText("先确认客户需求，再给出方案。")).toBeInTheDocument();

    act(() => {
      vi.advanceTimersByTime(3000);
    });
    expect(screen.queryByText("先确认客户需求，再给出方案。")).not.toBeInTheDocument();
  });

  it("collapses and expands sidebar", async () => {
    const user = userEvent.setup();
    renderRoom();

    const sidebar = screen.getByLabelText("AI 实时指导");
    expect(sidebar.className).toContain("w-full");

    await user.click(screen.getByRole("button", { name: "折叠侧边栏" }));
    expect(sidebar.className).toContain("w-12");

    await user.click(screen.getByRole("button", { name: "展开侧边栏" }));
    expect(sidebar.className).toContain("w-full");
  });
});
