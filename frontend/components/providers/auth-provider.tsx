"use client";

import { useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import { useAuthStore } from "@/store/auth-store";

const PUBLIC_PATHS = ["/", "/login", "/signup"];

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const { isAuthenticated, token } = useAuthStore();

  useEffect(() => {
    const isPublicPath = PUBLIC_PATHS.includes(pathname);
    
    if (!isAuthenticated && !token && !isPublicPath) {
      router.push("/login");
    }
  }, [isAuthenticated, token, pathname, router]);

  return <>{children}</>;
}
