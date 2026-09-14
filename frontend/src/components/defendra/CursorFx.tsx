import { useEffect, useRef, useState } from "react";

type Ripple = { id: number; x: number; y: number };

export function CursorFx() {
  const dotRef = useRef<HTMLDivElement>(null);
  const ringRef = useRef<HTMLDivElement>(null);
  const [ripples, setRipples] = useState<Ripple[]>([]);
  const idRef = useRef(0);

  useEffect(() => {
    let rx = 0, ry = 0, dx = 0, dy = 0, raf = 0;
    const onMove = (e: MouseEvent) => {
      dx = e.clientX; dy = e.clientY;
      if (dotRef.current) {
        dotRef.current.style.transform = `translate3d(${dx - 4}px, ${dy - 4}px, 0)`;
      }
    };
    const tick = () => {
      rx += (dx - rx) * 0.18;
      ry += (dy - ry) * 0.18;
      if (ringRef.current) {
        ringRef.current.style.transform = `translate3d(${rx - 18}px, ${ry - 18}px, 0)`;
      }
      raf = requestAnimationFrame(tick);
    };
    const onClick = (e: MouseEvent) => {
      const id = ++idRef.current;
      setRipples((r) => [...r, { id, x: e.clientX, y: e.clientY }]);
      setTimeout(() => setRipples((r) => r.filter((p) => p.id !== id)), 700);
    };
    const onOver = (e: MouseEvent) => {
      const t = e.target as HTMLElement;
      const interactive = t.closest("button, a, [role=button], input, textarea, select");
      if (ringRef.current) ringRef.current.dataset.hover = interactive ? "1" : "0";
    };
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseover", onOver);
    window.addEventListener("click", onClick);
    raf = requestAnimationFrame(tick);
    return () => {
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseover", onOver);
      window.removeEventListener("click", onClick);
      cancelAnimationFrame(raf);
    };
  }, []);

  return (
    <div className="pointer-events-none fixed inset-0 z-[9999]">
      <div
        ref={ringRef}
        data-hover="0"
        className="absolute left-0 top-0 h-9 w-9 rounded-full border border-green-500/60 transition-[width,height,border-color,background] duration-200 data-[hover=1]:h-12 data-[hover=1]:w-12 data-[hover=1]:bg-green-500/10 data-[hover=1]:border-green-400"
        style={{ boxShadow: "0 0 18px -2px #22c55e" }}
      />
      <div
        ref={dotRef}
        className="absolute left-0 top-0 h-2 w-2 rounded-full bg-green-500"
        style={{ boxShadow: "0 0 10px #22c55e" }}
      />
      {ripples.map((r) => (
        <span
          key={r.id}
          className="absolute h-6 w-6 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-green-500 animate-cursor-ripple"
          style={{ left: r.x, top: r.y, boxShadow: "0 0 24px #22c55e" }}
        />
      ))}
    </div>
  );
}