"use client";

import type { AccountCapabilities, ApiResponse } from "@english-ai-writing/shared";
import { useEffect, useRef, useState } from "react";

import { apiBaseUrl } from "@/lib/auth";
import { getAccountCapabilities } from "@/lib/school-data";

let capabilitiesRequest: Promise<AccountCapabilities> | null = null;

function sharedCapabilities() {
  capabilitiesRequest ??= getAccountCapabilities();
  return capabilitiesRequest;
}

function formatAudioTime(value: number) {
  if (!Number.isFinite(value) || value < 0) return "0:00";
  const minutes = Math.floor(value / 60);
  const seconds = Math.floor(value % 60).toString().padStart(2, "0");
  return `${minutes}:${seconds}`;
}

export function ReadAloudButton({
  taskId,
  text,
  context,
  label = "Read aloud",
}: {
  taskId: string;
  text: string;
  context: "PROMPT" | "WRITING";
  label?: string;
}) {
  const [enabled, setEnabled] = useState<boolean | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const audioUrlRef = useRef<string | null>(null);
  const audioRef = useRef<HTMLAudioElement>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);

  useEffect(() => {
    let active = true;
    void sharedCapabilities()
      .then((capabilities) => {
        if (active) setEnabled(capabilities.features.read_aloud);
      })
      .catch(() => {
        if (active) setEnabled(false);
      });
    return () => {
      active = false;
      if (audioUrlRef.current) URL.revokeObjectURL(audioUrlRef.current);
    };
  }, []);

  async function play() {
    if (!enabled || busy || !text.trim()) return;
    setBusy(true);
    setError("");
    try {
      const response = await fetch(`${apiBaseUrl}/api/media/speech`, {
        method: "POST",
        credentials: "include",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ task_id: taskId, context, text }),
      });
      if (!response.ok) {
        const body = (await response.json()) as ApiResponse<unknown>;
        throw new Error(body.success ? "Read aloud is unavailable." : body.message);
      }
      const nextUrl = URL.createObjectURL(await response.blob());
      if (audioUrlRef.current) URL.revokeObjectURL(audioUrlRef.current);
      audioUrlRef.current = nextUrl;
      setAudioUrl(nextUrl);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Read aloud is unavailable.");
    } finally {
      setBusy(false);
    }
  }

  async function togglePlayback() {
    const audio = audioRef.current;
    if (!audio) return;
    if (audio.paused) {
      await audio.play();
    } else {
      audio.pause();
    }
  }

  function seek(nextTime: number) {
    const audio = audioRef.current;
    if (!audio || !Number.isFinite(nextTime)) return;
    audio.currentTime = nextTime;
    setCurrentTime(nextTime);
  }

  if (enabled === false) {
    return (
      <span className="read-aloud-lock" title="Read aloud is included with School Pro">
        <span aria-hidden="true">◇</span> {label} · Pro
      </span>
    );
  }

  return (
    <div className="read-aloud-control">
      {!audioUrl ? (
        <button
          type="button"
          className="read-aloud-button"
          disabled={enabled !== true || busy || !text.trim()}
          onClick={() => void play()}
          aria-label={`${label}${busy ? ", generating audio" : ""}`}
        >
          {busy ? "Preparing voice…" : label}
        </button>
      ) : (
        <div className="read-aloud-button read-aloud-expanded" aria-label={`${label} audio player`}>
          <button
            type="button"
            className="read-aloud-transport"
            onClick={() => void togglePlayback()}
            aria-label={`${isPlaying ? "Pause" : "Play"} ${label.toLowerCase()}`}
          >
            {isPlaying ? "Pause" : "Play"}
          </button>
          <span className="read-aloud-time" aria-live="off">
            {formatAudioTime(currentTime)} / {formatAudioTime(duration)}
          </span>
          <input
            className="read-aloud-progress"
            type="range"
            min={0}
            max={Math.max(duration, 0.01)}
            step={0.1}
            value={Math.min(currentTime, Math.max(duration, 0.01))}
            onChange={(event) => seek(Number(event.target.value))}
            aria-label={`${label} progress`}
          />
          <audio
            ref={audioRef}
            className="read-aloud-native-audio"
            src={audioUrl}
            autoPlay
            onLoadedMetadata={(event) => setDuration(event.currentTarget.duration)}
            onDurationChange={(event) => setDuration(event.currentTarget.duration)}
            onTimeUpdate={(event) => setCurrentTime(event.currentTarget.currentTime)}
            onPlay={() => setIsPlaying(true)}
            onPause={() => setIsPlaying(false)}
            onEnded={() => setIsPlaying(false)}
          />
        </div>
      )}
      {error ? <small className="read-aloud-error" role="alert">{error}</small> : null}
    </div>
  );
}
