"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Scale, ArrowLeft, Shield } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { AdminUpload } from "@/components/admin/admin-upload";
import { StatsDashboard } from "@/components/admin/stats-dashboard";
import { useAuthStore } from "@/store/auth-store";

export default function AdminPage() {
  const router = useRouter();
  const { isAuthenticated, user } = useAuthStore();

  useEffect(() => {
    if (!isAuthenticated) {
      router.push("/login");
      return;
    }
    
    // Check admin role - for demo purposes, allow access
    // In production, you would check user?.role === "admin"
  }, [isAuthenticated, router, user]);

  if (!isAuthenticated) {
    return null;
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border">
        <div className="mx-auto max-w-6xl px-4 py-4 sm:px-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Link href="/research">
                <Button variant="ghost" size="icon">
                  <ArrowLeft className="h-5 w-5" />
                </Button>
              </Link>
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-accent">
                  <Scale className="h-6 w-6 text-accent-foreground" />
                </div>
                <div>
                  <h1 className="text-xl font-semibold">Admin Dashboard</h1>
                  <p className="text-sm text-muted-foreground">
                    Manage knowledge base
                  </p>
                </div>
              </div>
            </div>
            <div className="flex items-center gap-2 rounded-lg bg-accent/10 px-3 py-1.5">
              <Shield className="h-4 w-4 text-accent" />
              <span className="text-sm font-medium text-accent">Admin</span>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
        <Tabs defaultValue="stats" className="space-y-6">
          <TabsList className="bg-muted">
            <TabsTrigger value="stats">Statistics</TabsTrigger>
            <TabsTrigger value="upload">Document Upload</TabsTrigger>
          </TabsList>

          <TabsContent value="stats" className="mt-6">
            <StatsDashboard />
          </TabsContent>

          <TabsContent value="upload" className="mt-6">
            <div className="space-y-6">
              <div>
                <h2 className="text-xl font-semibold">Upload Documents</h2>
                <p className="text-sm text-muted-foreground mt-1">
                  Upload legal documents to add them to the knowledge base for AI-powered research.
                </p>
              </div>
              <AdminUpload />
            </div>
          </TabsContent>
        </Tabs>
      </main>
    </div>
  );
}
