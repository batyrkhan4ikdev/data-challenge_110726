import { t } from '../i18n.js';
import { h } from './dom.js';

export interface AudioPlayerOptions {
  src: string | null;
  /** id реального <audio>; на странице он один (#cqa-call-audio). */
  id?: string | null;
  /** Размер файла в байтах, если известен; без него размер не показывается. */
  loadSize?: () => Promise<number | null>;
  /** Показать сообщение о сбое загрузки/нехватке записи. */
  onError?: () => void;
  onReady?: () => void;
}

export interface AudioPlayer {
  el: HTMLElement;
  audio: HTMLAudioElement;
}

const SPEEDS = [0.75, 1, 1.25, 1.5, 2];
const SKIP_S = 10;

const ICONS = {
  play: 'M8 5v14l11-7z',
  pause: 'M6 5h4v14H6zM14 5h4v14h-4z',
  back: 'M12 5V1L7 6l5 5V7a6 6 0 1 1-6 6H4a8 8 0 1 0 8-8z',
  forward: 'M12 5V1l5 5-5 5V7a6 6 0 1 0 6 6h2a8 8 0 1 1-8-8z',
  volume: 'M3 9v6h4l5 5V4L7 9zm13.5 3a4.5 4.5 0 0 0-2.5-4v8a4.5 4.5 0 0 0 2.5-4z',
  muted: 'M3 9v6h4l5 5V4L7 9zm13.6 3 2.4-2.4-1.4-1.4-2.4 2.4-2.4-2.4-1.4 1.4 2.4 2.4-2.4 2.4 1.4 1.4 2.4-2.4 2.4 2.4 1.4-1.4z',
};

function icon(path: string): SVGSVGElement {
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('viewBox', '0 0 24 24');
  svg.setAttribute('aria-hidden', 'true');
  svg.setAttribute('focusable', 'false');
  svg.classList.add('cqa-player-icon');
  const p = document.createElementNS('http://www.w3.org/2000/svg', 'path');
  p.setAttribute('d', path);
  svg.appendChild(p);
  return svg;
}

function setIcon(btn: HTMLElement, path: string): void {
  btn.querySelector('path')?.setAttribute('d', path);
}

export function formatTime(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds < 0) return '--:--';
  const s = Math.floor(seconds);
  const hours = Math.floor(s / 3600);
  const mm = Math.floor((s % 3600) / 60);
  const ss = String(s % 60).padStart(2, '0');
  return hours > 0 ? `${hours}:${String(mm).padStart(2, '0')}:${ss}` : `${String(mm).padStart(2, '0')}:${ss}`;
}

/** Компактный плеер вокруг настоящего HTMLAudioElement: пауза, перемотка, скорость, громкость, буфер и размер файла. */
export function createAudioPlayer(opts: AudioPlayerOptions): AudioPlayer {
  const audio = h('audio', { class: 'cqa-audio', id: opts.id ?? null, preload: 'none', src: opts.src || null });

  const btn = (label: string, path: string, onclick: () => void): HTMLButtonElement =>
    h('button', { type: 'button', class: 'cqa-player-btn', 'aria-label': label, title: label, onclick }, icon(path));

  const play = btn(t.result.player.play, ICONS.play, () => {
    if (audio.paused) void audio.play().catch(() => opts.onError?.());
    else audio.pause();
  });
  play.classList.add('cqa-player-btn--main');
  const skip = (delta: number) => () => {
    const end = Number.isFinite(audio.duration) ? audio.duration : Number.POSITIVE_INFINITY;
    audio.currentTime = Math.min(Math.max(0, audio.currentTime + delta), end);
  };
  const back = btn(t.result.player.back, ICONS.back, skip(-SKIP_S));
  const forward = btn(t.result.player.forward, ICONS.forward, skip(SKIP_S));

  const current = h('span', { class: 'cqa-player-time' }, formatTime(0));
  const total = h('span', { class: 'cqa-player-time' }, '--:--');
  const size = h('span', { class: 'cqa-player-size', hidden: true });

  const seek = h('input', {
    type: 'range',
    class: 'cqa-player-seek',
    min: '0',
    max: '0',
    step: '0.1',
    value: '0',
    'aria-label': t.result.player.seek,
  });
  const track = h('div', { class: 'cqa-player-track' }, seek);

  const speed = h('button', { type: 'button', class: 'cqa-player-speed', title: t.result.player.speed, 'aria-label': t.result.player.speed }, t.result.player.speedValue(1));
  speed.addEventListener('click', () => {
    const next = SPEEDS[(SPEEDS.indexOf(audio.playbackRate) + 1) % SPEEDS.length] ?? 1;
    audio.playbackRate = next;
  });

  const mute = btn(t.result.player.mute, ICONS.volume, () => {
    audio.muted = !audio.muted;
  });
  const volume = h('input', {
    type: 'range',
    class: 'cqa-player-volume',
    min: '0',
    max: '1',
    step: '0.05',
    value: '1',
    'aria-label': t.result.player.volume,
  });
  volume.addEventListener('input', () => {
    audio.volume = Number(volume.value);
    audio.muted = audio.volume === 0;
  });

  const fraction = (value: number): string => {
    const d = audio.duration;
    return Number.isFinite(d) && d > 0 ? `${Math.min(100, Math.max(0, (value / d) * 100)).toFixed(2)}%` : '0%';
  };
  const paintProgress = (): void => {
    const now = audio.currentTime;
    seek.value = String(now);
    seek.setAttribute('aria-valuetext', `${formatTime(now)} / ${formatTime(audio.duration)}`);
    track.style.setProperty('--cqa-p', fraction(now));
    current.textContent = formatTime(now);
  };
  const paintBuffered = (): void => {
    let end = 0;
    for (let i = 0; i < audio.buffered.length; i++) {
      if (audio.buffered.start(i) <= audio.currentTime + 0.5) end = Math.max(end, audio.buffered.end(i));
    }
    track.style.setProperty('--cqa-b', fraction(end));
  };
  const paintDuration = (): void => {
    total.textContent = formatTime(audio.duration);
    seek.max = Number.isFinite(audio.duration) ? String(audio.duration) : '0';
    paintProgress();
    paintBuffered();
  };

  seek.addEventListener('input', () => {
    audio.currentTime = Number(seek.value);
    paintProgress();
  });
  audio.addEventListener('timeupdate', paintProgress);
  audio.addEventListener('seeked', () => {
    paintProgress();
    paintBuffered();
  });
  audio.addEventListener('progress', paintBuffered);
  audio.addEventListener('durationchange', paintDuration);
  audio.addEventListener('loadedmetadata', () => {
    paintDuration();
    opts.onReady?.();
  });
  audio.addEventListener('error', () => opts.onError?.());
  const syncPlay = (): void => {
    const label = audio.paused ? t.result.player.play : t.result.player.pause;
    play.setAttribute('aria-label', label);
    play.title = label;
    setIcon(play, audio.paused ? ICONS.play : ICONS.pause);
  };
  audio.addEventListener('play', syncPlay);
  audio.addEventListener('pause', syncPlay);
  audio.addEventListener('ended', syncPlay);
  audio.addEventListener('ratechange', () => {
    speed.textContent = t.result.player.speedValue(audio.playbackRate);
  });
  audio.addEventListener('volumechange', () => {
    const off = audio.muted || audio.volume === 0;
    const label = off ? t.result.player.unmute : t.result.player.mute;
    mute.setAttribute('aria-label', label);
    mute.title = label;
    setIcon(mute, off ? ICONS.muted : ICONS.volume);
    volume.value = audio.muted ? '0' : String(audio.volume);
  });

  if (!opts.src) {
    for (const control of [play, back, forward, seek, speed, mute, volume]) control.disabled = true;
  }
  if (opts.src && opts.loadSize) {
    void opts.loadSize().then(
      (bytes) => {
        if (bytes === null || bytes === undefined || !(bytes > 0)) return;
        size.textContent = t.result.player.size(bytes);
        size.hidden = false;
      },
      () => undefined,
    );
  }

  const el = h(
    'div',
    { class: 'cqa-player', role: 'group', 'aria-label': t.result.audio },
    audio,
    h(
      'div',
      { class: 'cqa-player-row' },
      h('div', { class: 'cqa-player-transport' }, back, play, forward),
      h('div', { class: 'cqa-player-clock' }, current, ' / ', total, size),
      h('div', { class: 'cqa-player-extras' }, speed, mute, volume),
    ),
    track,
  );
  return { el, audio };
}
