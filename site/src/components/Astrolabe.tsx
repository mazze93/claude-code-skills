/**
 * The navigator. Each plugin is a ring; each skill is a star on it. Hovering a
 * ring traces its constellation and names it; clicking scrolls to the slab.
 *
 * This is the navigation, not an illustration beside it — which is why it is an
 * island rather than static SVG: it holds selection state and drives the page.
 * Keyboard-operable, and it degrades to a plain labelled list of links when
 * reduced motion is requested, because an instrument nobody can steer is decor.
 */
import { useCallback, useMemo, useState } from 'react';

export interface AstrolabeRing {
  name: string;
  skills: string[];
  paid: boolean;
}
export interface Props {
  rings: AstrolabeRing[];
}

const SIZE = 520;
const C = SIZE / 2;

export default function Astrolabe({ rings }: Props) {
  const [active, setActive] = useState<string | null>(null);

  const geometry = useMemo(() => {
    const inner = 78;
    const gap = (C - inner - 26) / Math.max(rings.length - 1, 1);
    return rings.map((ring, i) => {
      const r = inner + gap * i;
      const spin = (i % 2 === 0 ? 1 : -1) * (i * 11);
      const stars = ring.skills.map((s, j) => {
        const a = ((j / ring.skills.length) * 360 + spin - 90) * (Math.PI / 180);
        return { name: s, x: C + r * Math.cos(a), y: C + r * Math.sin(a) };
      });
      return { ...ring, r, stars };
    });
  }, [rings]);

  const go = useCallback((name: string) => {
    const el = document.getElementById(`plugin-${name}`);
    el?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    el?.focus({ preventScroll: true });
  }, []);

  return (
    <figure className="astrolabe" aria-label="Plugin navigator">
      <svg viewBox={`0 0 ${SIZE} ${SIZE}`} role="group" aria-label="Constellation of plugins and their skills">
        <circle cx={C} cy={C} r={C - 8} className="plate" />
        {[0, 45, 90, 135].map((d) => (
          <line key={d} x1={C} y1={16} x2={C} y2={SIZE - 16}
                className="graticule" transform={`rotate(${d} ${C} ${C})`} />
        ))}
        {geometry.map((ring) => {
          const on = active === ring.name;
          return (
            <g key={ring.name}
               className={`ring${on ? ' on' : ''}${ring.paid ? ' paid' : ''}`}
               onMouseEnter={() => setActive(ring.name)}
               onMouseLeave={() => setActive(null)}>
              <circle cx={C} cy={C} r={ring.r} className="orbit" />
              <polygon
                points={ring.stars.map((s) => `${s.x},${s.y}`).join(' ')}
                className="trace" />
              {ring.stars.map((s) => (
                <circle key={s.name} cx={s.x} cy={s.y} r={on ? 4.5 : 2.6} className="star">
                  <title>{`${s.name} — ${ring.name}`}</title>
                </circle>
              ))}
              <circle cx={C} cy={C - ring.r} r={13} className="hit"
                      tabIndex={0} role="button"
                      aria-label={`${ring.name}: ${ring.skills.length} skills`}
                      onFocus={() => setActive(ring.name)}
                      onBlur={() => setActive(null)}
                      onClick={() => go(ring.name)}
                      onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); go(ring.name); } }} />
            </g>
          );
        })}
        <circle cx={C} cy={C} r={30} className="hub" />
        <text x={C} y={C - 3} className="hub-l" textAnchor="middle">MZ</text>
        <text x={C} y={C + 11} className="hub-s" textAnchor="middle">93</text>
      </svg>
      <figcaption className="coord" aria-live="polite">
        {active
          ? `${active} · ${rings.find((r) => r.name === active)?.skills.length} skills`
          : `${rings.length} rings · ${rings.reduce((n, r) => n + r.skills.length, 0)} stars`}
      </figcaption>
    </figure>
  );
}
