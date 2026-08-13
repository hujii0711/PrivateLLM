import type { ReactElement, ReactNode } from "react";
import { render, type RenderOptions } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useUiStore, initialUiState } from "@/store/uiStore";

/**
 * 테스트에서 Provider가 필요한 컴포넌트를 렌더할 때 사용하는 래퍼.
 *
 *   import { renderWithProviders } from "@/test/renderWithProviders";
 *   renderWithProviders(<SomeComponent />);
 *
 * - QueryClient는 테스트마다 새로 만들고 retry를 끈다(실패 케이스가 지연 없이 끝나도록).
 * - zustand store는 테스트마다 초기 상태로 되돌려 테스트 간 상태 누수를 막는다.
 */
export function makeTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0, staleTime: 0 },
      mutations: { retry: false },
    },
  });
}

/** zustand UI store를 초기 상태로 리셋(액션은 유지). 각 테스트 beforeEach에서 호출. */
export function resetUiStore() {
  useUiStore.setState(initialUiState);
}

export function renderWithProviders(
  ui: ReactElement,
  options?: Omit<RenderOptions, "wrapper">,
) {
  const queryClient = makeTestQueryClient();

  function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  }

  return {
    queryClient,
    ...render(ui, { wrapper: Wrapper, ...options }),
  };
}
