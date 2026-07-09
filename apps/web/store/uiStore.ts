import { create } from "zustand";
import { devtools, persist } from "zustand/middleware";

export type Theme = "light" | "dark";

/**
 * 순수 "클라이언트 UI 상태"만 담는 store.
 *
 * 여기에 서버 데이터(세션 목록, 사용자 정보 등)를 미러링하지 말 것.
 * 서버 상태의 단일 출처(SSOT)는 react-query 캐시다.
 * 이 store에는 "활성 세션 ID" 같은 참조/선택 상태와 UI 토글만 둔다.
 *
 * 사용 시 셀렉터로 구독해 불필요한 리렌더를 막는다.
 *   const sidebarOpen = useUiStore((s) => s.sidebarOpen);
 */
export interface UiState {
  /** 현재 보고 있는 대화 세션 ID(서버 데이터는 react-query가 보유, 여기엔 선택값만) */
  activeSessionId: string | null;
  sidebarOpen: boolean;
  theme: Theme;

  setActiveSession: (id: string | null) => void;
  toggleSidebar: () => void;
  setSidebarOpen: (open: boolean) => void;
  setTheme: (theme: Theme) => void;
}

export const initialUiState: Pick<
  UiState,
  "activeSessionId" | "sidebarOpen" | "theme"
> = {
  activeSessionId: null,
  sidebarOpen: true,
  theme: "light",
};

export const useUiStore = create<UiState>()(
  devtools(
    persist(
      (set) => ({
        ...initialUiState,
        setActiveSession: (id) => set({ activeSessionId: id }),
        toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
        setSidebarOpen: (open) => set({ sidebarOpen: open }),
        setTheme: (theme) => set({ theme }),
      }),
      {
        name: "ui-store",
        // UI 환경설정만 영속화한다. 활성 세션 ID 같은 일시적 선택 상태는 저장하지 않는다.
        partialize: (s) => ({ theme: s.theme, sidebarOpen: s.sidebarOpen }),
      },
    ),
    { name: "ui-store" },
  ),
);
