"use client";
import { useState } from "react";
import {
  isServer,
  QueryClient,
  QueryClientProvider,
} from "@tanstack/react-query";
// import { ReactQueryDevtools } from "@tanstack/react-query-devtools";

function makeQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        // 서버에서 즉시 refetch 되는 것을 막아 SSR 하이드레이션 직후 깜빡임 방지
        staleTime: 60 * 1000,
      },
    },
  });
}

// 브라우저에서는 단일 인스턴스를 재사용한다.
// 서버에서는 매 요청마다 새 인스턴스를 만들어 사용자 간 캐시 공유(누수)를 막는다.
let browserQueryClient: QueryClient | undefined;

function getQueryClient() {
  if (isServer) {
    return makeQueryClient();
  }
  if (!browserQueryClient) {
    browserQueryClient = makeQueryClient();
  }
  return browserQueryClient;
}

export default function Providers({
  children,
}: {
  children: React.ReactNode;
}) {
  // getQueryClient()는 브라우저에서 항상 같은 인스턴스를 돌려주지만,
  // useState로 한 번 더 고정해 Strict Mode 중복 렌더에도 안전하게 한다.
  const [queryClient] = useState(getQueryClient);

  return (
    <QueryClientProvider client={queryClient}>
      {children}
      {/* {process.env.NODE_ENV === "development" && (
        <ReactQueryDevtools initialIsOpen={false} />
      )} */}
    </QueryClientProvider>
  );
}
