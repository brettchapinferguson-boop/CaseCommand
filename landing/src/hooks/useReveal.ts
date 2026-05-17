import { useEffect, useRef, useState } from 'react';

/**
 * Adds an `in-view` class to the element once it enters the viewport.
 * Use with the `.reveal` utility (defined in index.css) for fade-up effects.
 */
export function useReveal<T extends HTMLElement>(options?: IntersectionObserverInit) {
  const ref = useRef<T | null>(null);
  const [shown, setShown] = useState(false);

  useEffect(() => {
    if (!ref.current || shown) return;
    if (typeof IntersectionObserver === 'undefined') {
      setShown(true);
      return;
    }
    const node = ref.current;
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            setShown(true);
            observer.disconnect();
          }
        });
      },
      { threshold: 0.15, rootMargin: '0px 0px -10% 0px', ...options }
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, [shown, options]);

  return { ref, shown };
}
