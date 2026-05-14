"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import {
  Scale,
  ArrowRight,
  FileText,
  Brain,
  Shield,
  MessageSquare,
  CheckCircle2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { useAuthStore } from "@/store/auth-store";

const features = [
  {
    icon: <Brain className="h-6 w-6" />,
    title: "RAG-Powered Answers",
    description:
      "Retrieval-Augmented Generation ensures answers are grounded in real legal documents, dramatically reducing hallucinations.",
  },
  {
    icon: <FileText className="h-6 w-6" />,
    title: "Trusted Citations",
    description:
      "Every answer comes with verifiable sources from your legal document database, with similarity scores for confidence.",
  },
  {
    icon: <Shield className="h-6 w-6" />,
    title: "Secure & Private",
    description:
      "Your research stays private with enterprise-grade security. Internal documents never leave your environment.",
  },
  {
    icon: <MessageSquare className="h-6 w-6" />,
    title: "Conversation Memory",
    description:
      "Continue where you left off. All your research sessions are saved and searchable for future reference.",
  },
];

const benefits = [
  "Semantic search across your entire legal knowledge base",
  "Real-time streaming responses for instant feedback",
  "Hybrid search combining internal docs and web sources",
  "Admin dashboard for document ingestion and metrics",
];

export default function LandingPage() {
  const router = useRouter();
  const { isAuthenticated } = useAuthStore();

  // No automatic redirect from landing page - let user explore features
  useEffect(() => {
    // Optionally pre-fetch research if already logged in, but don't force jump
    // if (isAuthenticated) router.prefetch("/research");
  }, [isAuthenticated, router]);

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border">
        <div className="mx-auto max-w-6xl px-4 py-4 sm:px-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-accent">
                <Scale className="h-6 w-6 text-accent-foreground" />
              </div>
              <span className="text-xl font-semibold">Legal Research AI</span>
            </div>
            <div className="flex items-center gap-3">
              <Button variant="ghost" asChild>
                <Link href="/login">Sign in</Link>
              </Button>
              <Button asChild>
                <Link href="/signup">
                  Get started
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Link>
              </Button>
            </div>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="py-20 sm:py-32">
        <div className="mx-auto max-w-6xl px-4 sm:px-6">
          <div className="mx-auto max-w-3xl text-center">
            <h1 className="text-4xl font-bold tracking-tight sm:text-6xl text-balance">
              AI-powered legal research with{" "}
              <span className="text-accent">trusted citations</span>
            </h1>
            <p className="mt-6 text-lg text-muted-foreground leading-relaxed text-pretty">
              Reduce hallucinations in your legal research with our RAG-powered
              system. Get accurate answers grounded in real legal documents with
              verifiable sources.
            </p>
            <div className="mt-10 flex items-center justify-center gap-4">
              <Button size="lg" className="h-12 px-8 text-base" asChild>
                <Link href="/signup">
                  Start researching
                  <ArrowRight className="ml-2 h-5 w-5" />
                </Link>
              </Button>
              <Button variant="outline" size="lg" className="h-12 px-8 text-base" asChild>
                <Link href="/login">Sign in</Link>
              </Button>
            </div>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="py-20 bg-card border-y border-border">
        <div className="mx-auto max-w-6xl px-4 sm:px-6">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-bold">Built for legal professionals</h2>
            <p className="mt-4 text-muted-foreground text-lg">
              Everything you need for accurate, efficient legal research
            </p>
          </div>

          <div className="grid gap-8 sm:grid-cols-2 lg:grid-cols-4">
            {features.map((feature, index) => (
              <div
                key={index}
                className="group rounded-xl border border-border bg-background p-6 transition-all hover:border-accent/50"
              >
                <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-accent/10 text-accent group-hover:bg-accent group-hover:text-accent-foreground transition-colors">
                  {feature.icon}
                </div>
                <h3 className="mt-4 font-semibold">{feature.title}</h3>
                <p className="mt-2 text-sm text-muted-foreground leading-relaxed">
                  {feature.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Benefits */}
      <section className="py-20">
        <div className="mx-auto max-w-6xl px-4 sm:px-6">
          <div className="grid gap-12 lg:grid-cols-2 lg:gap-16 items-center">
            <div>
              <h2 className="text-3xl font-bold">
                Research smarter, not harder
              </h2>
              <p className="mt-4 text-muted-foreground text-lg leading-relaxed">
                Our AI understands legal context and retrieves the most relevant
                documents from your knowledge base, ensuring every answer is
                backed by real sources.
              </p>

              <ul className="mt-8 space-y-4">
                {benefits.map((benefit, index) => (
                  <li key={index} className="flex items-start gap-3">
                    <CheckCircle2 className="h-6 w-6 text-accent shrink-0 mt-0.5" />
                    <span className="text-foreground">{benefit}</span>
                  </li>
                ))}
              </ul>

              <div className="mt-10">
                <Link href="/signup">
                  <Button size="lg" className="h-12 px-8">
                    Get started for free
                    <ArrowRight className="ml-2 h-5 w-5" />
                  </Button>
                </Link>
              </div>
            </div>

            <div className="rounded-2xl border border-border bg-card p-8">
              <div className="space-y-4">
                <div className="flex items-center gap-3 rounded-lg bg-primary/10 p-4">
                  <div className="h-8 w-8 rounded-full bg-primary flex items-center justify-center">
                    <span className="text-sm font-medium text-primary-foreground">
                      You
                    </span>
                  </div>
                  <p className="text-sm">
                    What are the key precedents for breach of fiduciary duty?
                  </p>
                </div>

                <div className="flex items-start gap-3 rounded-lg border border-border p-4">
                  <div className="h-8 w-8 rounded-full bg-accent flex items-center justify-center shrink-0">
                    <Scale className="h-4 w-4 text-accent-foreground" />
                  </div>
                  <div className="space-y-3">
                    <p className="text-sm leading-relaxed">
                      Based on the legal documents in your knowledge base, the
                      key precedents for breach of fiduciary duty include...
                    </p>
                    <div className="flex gap-2 flex-wrap">
                      <span className="inline-flex items-center rounded-md bg-accent/20 px-2 py-1 text-xs text-accent">
                        Smith v. Jones (2019) - 94% match
                      </span>
                      <span className="inline-flex items-center rounded-md bg-accent/20 px-2 py-1 text-xs text-accent">
                        Corporate Law Review - 89% match
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-20 bg-card border-t border-border">
        <div className="mx-auto max-w-6xl px-4 sm:px-6 text-center">
          <h2 className="text-3xl font-bold">Ready to transform your legal research?</h2>
          <p className="mt-4 text-muted-foreground text-lg">
            Join legal professionals using AI-powered research with trusted citations.
          </p>
          <div className="mt-10 flex items-center justify-center gap-4">
            <Link href="/signup">
              <Button size="lg" className="h-12 px-8 text-base">
                Start for free
                <ArrowRight className="ml-2 h-5 w-5" />
              </Button>
            </Link>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-border py-8">
        <div className="mx-auto max-w-6xl px-4 sm:px-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Scale className="h-5 w-5 text-accent" />
              <span className="font-medium">Legal Research AI</span>
            </div>
            <p className="text-sm text-muted-foreground">
              Built for legal professionals
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}
