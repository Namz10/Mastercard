import { useEffect, useState, type ReactNode, type RefObject } from "react";
import { cn } from "@/lib/utils";
import { usePrefersReducedMotion } from "@/hooks/usePrefersReducedMotion";

export interface TimelineAnimationProps {
  children: ReactNode;
  className?: string;
  animationNum?: number;
  timelineRef?: RefObject<HTMLElement | null>;
  staggerMs?: number;
  rootMargin?: string;
}

export function TimelineAnimation({
  children,
  className,
  animationNum = 0,
  timelineRef,
  staggerMs = 70,
  rootMargin = "0px 0px -6% 0px",
}: TimelineAnimationProps) {
  const reduced = usePrefersReducedMotion();
  const [visible, setVisible] = useState(reduced);

  useEffect(() => {
    if (reduced) return;
    const node = timelineRef?.current;
    if (!node) {
      setVisible(true);
      return;
    }

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setVisible(true);
          observer.disconnect();
        }
      },
      { threshold: 0.08, rootMargin },
    );

    observer.observe(node);
    return () => observer.disconnect();
  }, [reduced, rootMargin, timelineRef]);

  return (
    <div
      className={cn(
        "timeline-animation",
        visible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-2",
        className,
      )}
      style={
        reduced
          ? undefined
          : {
              transitionProperty: "opacity, transform",
              transitionDuration: "140ms",
              transitionTimingFunction: "cubic-bezier(0.22, 1, 0.36, 1)",
              transitionDelay: visible ? `${animationNum * staggerMs}ms` : "0ms",
            }
      }
    >
      {children}
    </div>
  );
}
