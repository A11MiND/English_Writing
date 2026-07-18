"use client";

import { FormEvent, useEffect, useRef, useState, type CSSProperties } from "react";
import { useRouter } from "next/navigation";

import { currentUser, login, routeForRole } from "@/lib/auth";

type StoryMoment = {
  word: string;
  phrase: string;
  side: "left" | "right";
  art?: string;
  artAlt?: string;
};

const storyMoments: StoryMoment[] = [
  {
    word: "imagine",
    phrase: "I imagine a forest where stars grow like tiny flowers.",
    side: "left",
    art: "/story-treehouse.png",
    artAlt: "A tiny tree-stump story house with a blue bird",
  },
  { word: "curious", phrase: "I ask questions and love finding new things.", side: "right" },
  {
    word: "brave",
    phrase: "I try my best and share my ideas with the world.",
    side: "left",
    art: "/story-mouse-books.png",
    artAlt: "A brave little mouse holding a flag on a stack of books",
  },
  { word: "kind", phrase: "I write with kindness and help my friends shine.", side: "right" },
  {
    word: "discover",
    phrase: "I explore new words and ideas every day.",
    side: "left",
    art: "/story-botanical-book.png",
    artAlt: "An open botanical book filled with painted wildflowers",
  },
  { word: "wonder", phrase: "I see the magic in small moments and big dreams.", side: "right" },
];

export function LoginPage() {
  const router = useRouter();
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const emailInputRef = useRef<HTMLInputElement>(null);
  const passwordInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    let active = true;
    async function checkSession() {
      const user = await currentUser();
      if (active && user) {
        router.replace(routeForRole(user.role));
      }
    }
    void checkSession();
    return () => {
      active = false;
    };
  }, [router]);

  useEffect(() => {
    const elements = Array.from(document.querySelectorAll<HTMLElement>("[data-story-reveal]"));
    if (!("IntersectionObserver" in window)) {
      elements.forEach((element) => element.classList.add("is-visible"));
      return;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-visible");
          } else {
            entry.target.classList.remove("is-visible");
          }
        });
      },
      { rootMargin: "0px 0px -12%", threshold: 0.16 },
    );

    elements.forEach((element) => observer.observe(element));
    return () => observer.disconnect();
  }, []);

  async function submitLogin() {
    if (loading) return;
    const currentEmail = emailInputRef.current?.value.trim() ?? "";
    const currentPassword = passwordInputRef.current?.value ?? "";
    setLoading(true);
    setError("");
    try {
      const user = await login(currentEmail, currentPassword);
      router.replace(routeForRole(user.role));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sign in failed.");
    } finally {
      setLoading(false);
    }
  }

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await submitLogin();
  }

  return (
    <main className="login-story-page">
      <img className="login-nature-backdrop" src="/login-botanical-journey.png" alt="" aria-hidden="true" />

      <section className="login-opening" aria-labelledby="login-story-title">
        <div className="login-opening-inner">
          <div className="login-hero-mascot" data-story-reveal>
            <img src="/ai-coach-fox.png" alt="Pip the fox writing in a notebook" />
          </div>

          <div className="login-hero-copy" data-story-reveal>
            <h1 id="login-story-title">Every great story starts with a little wonder.</h1>
            <p>
              A gentle place to imagine, explore, and write with confidence—one idea at a time. For curious minds. For kind hearts. For every young writer.
            </p>
          </div>
        </div>

        <a className="login-scroll-cue" href="#word-journey" aria-label="Scroll to begin your writing journey">
          <span>Scroll to begin your writing journey</span>
        </a>
      </section>

      <section className="login-word-journey" id="word-journey" aria-label="Words for a young writer">
        <div className="login-word-path">
          <img className="login-golden-trail" src="/story-golden-trail.png" alt="" aria-hidden="true" />
          {storyMoments.map((item, index) => (
            <article
              className={`login-story-moment login-story-moment-${item.side} ${item.art ? "login-story-moment-has-art" : ""}`}
              key={item.word}
            >
              <div
                className={`login-word login-word-${item.word}`}
                data-story-reveal
                style={{ "--word-delay": `${(index % 2) * 70}ms` } as CSSProperties}
              >
                <h3>{item.word}</h3>
                <p>“{item.phrase}”</p>
              </div>
              {item.art ? (
                <div
                  className={`login-story-object login-story-object-${item.word}`}
                  data-story-reveal
                  style={{ "--word-delay": `${120 + (index % 2) * 70}ms` } as CSSProperties}
                >
                  <img src={item.art} alt={item.artAlt ?? ""} />
                </div>
              ) : null}
            </article>
          ))}
        </div>
      </section>

      <section className="login-arrival" id="sign-in" aria-labelledby="sign-in-title">
        <div className="login-arrival-copy" data-story-reveal>
          <img src="/brand-fox.png" alt="" />
          <p>Your writing space is ready.</p>
        </div>

        <section className="login-card" data-story-reveal>
          <div className="login-card-heading">
            <h2 id="sign-in-title">Welcome back, writer.</h2>
            <p>Sign in to continue your writing journey.</p>
          </div>

          <form className="login-form" onSubmit={onSubmit}>
            <div className="field">
              <label htmlFor="email">Email</label>
              <input
                id="email"
                ref={emailInputRef}
                className="input"
                type="email"
                autoComplete="email"
                placeholder="name@example.com"
                required
              />
            </div>

            <div className="field">
              <label htmlFor="password">Password</label>
              <input
                id="password"
                ref={passwordInputRef}
                className="input"
                type="password"
                autoComplete="current-password"
                placeholder="Enter your password"
                required
              />
            </div>

            {error ? <p className="notice-error">{error}</p> : null}

            <button type="submit" disabled={loading} className="btn btn-dark btn-block login-submit">
              {loading ? "Signing in..." : "Sign in"}
            </button>

            <p className="login-managed-help">
              Pupils receive sign-in details from a teacher. Teachers use the account provided by their organisation.
            </p>
          </form>
        </section>
      </section>
    </main>
  );
}
