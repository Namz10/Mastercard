import { useMemo, type CSSProperties } from "react";

import GLOBE_STUDY_SOURCE from "./globe-study-document.html?raw";

// Verbatim (trimmed to the globe study) from MengTo/threeui, MIT licensed:
// src/shaders/text-path-studies/sources/text-on-a-path-ii.html

export type GlobeStudyProps = {
  mode?: "dark" | "light";
  scale?: number;
  opacity?: number;
  hue?: number;
  saturation?: number;
  brightness?: number;
  className?: string;
  style?: CSSProperties;
};

export const GLOBE_STUDY_DEFAULTS = {
  mode: "dark",
  scale: 1,
  opacity: 1,
  hue: 0,
  saturation: 1,
  brightness: 1,
} as const;

function clamp(value: number, minimum: number, maximum: number) {
  return Math.min(maximum, Math.max(minimum, value));
}

function focusStyles(mode: "dark" | "light") {
  const selected = 1;
  const surface = mode === "light" ? "#f3f5f8" : "#08090a";
  const themeStyles =
    mode === "light"
      ? `
      :root {
        color-scheme: light;
        --bg: #f3f5f8;
        --line: rgba(20, 24, 32, .055);
        --line-strong: rgba(20, 24, 32, .10);
        --fig: rgba(20, 24, 32, .42);
        --title: #171922;
        --copy: rgba(20, 24, 32, .62);
      }
    `
      : ":root { color-scheme: dark; }";

  return `<style id="threeui-study-focus">
    ${themeStyles}
    html, body, .frame {
      width: 100% !important;
      height: 100% !important;
      overflow: hidden !important;
    }
    body { margin: 0 !important; background: ${surface} !important; }
    .frame { padding: 0 !important; background: ${surface} !important; }
    header { display: none !important; }
    .grid {
      display: block !important;
      width: 100% !important;
      height: 100% !important;
      overflow: hidden !important;
    }
    .fig { display: none !important; }
    .fig:nth-child(${selected}) {
      display: flex !important;
      width: 100% !important;
      height: 100% !important;
      padding: 0 !important;
    }
    .fig::before, .fig::after, .fignum, .fig h3, .fig p { display: none !important; }
    .art {
      display: flex !important;
      width: 100% !important;
      height: 100% !important;
      max-height: none !important;
      margin: 0 !important;
      align-items: center !important;
      justify-content: center !important;
    }
    .plate {
      width: min(100cqw, 100cqh) !important;
      height: min(100cqw, 100cqh) !important;
    }
  </style>`;
}

const AUTHORED_FIGURE_INK = "var INK  = '226,228,233';";

function replaceRequired(source: string, authored: string, focused: string) {
  if (!source.includes(authored)) {
    throw new Error(`Globe study source adapter could not find: ${authored}`);
  }
  return source.replace(authored, focused);
}

function focusedDocument(mode: "dark" | "light") {
  const source =
    mode === "light"
      ? replaceRequired(
          GLOBE_STUDY_SOURCE,
          AUTHORED_FIGURE_INK,
          "var INK  = '38,40,48';",
        )
      : GLOBE_STUDY_SOURCE;

  return source
    .replace(/<title>[\s\S]*?<\/title>/i, `<title>Globe — ThreeUI</title>`)
    .replace("</head>", `${focusStyles(mode)}
</head>`);
}

export default function GlobeStudy({
  mode = GLOBE_STUDY_DEFAULTS.mode,
  scale = GLOBE_STUDY_DEFAULTS.scale,
  opacity = GLOBE_STUDY_DEFAULTS.opacity,
  hue = GLOBE_STUDY_DEFAULTS.hue,
  saturation = GLOBE_STUDY_DEFAULTS.saturation,
  brightness = GLOBE_STUDY_DEFAULTS.brightness,
  className,
  style,
}: GlobeStudyProps) {
  const safeMode = mode === "light" ? "light" : "dark";
  const document = useMemo(() => focusedDocument(safeMode), [safeMode]);
  const boundedScale = clamp(scale, 0.65, 1.5);
  const boundedOpacity = clamp(opacity, 0.1, 1);
  const boundedHue = clamp(hue, -180, 180);
  const boundedSaturation = clamp(saturation, 0, 2);
  const boundedBrightness = clamp(brightness, 0.4, 1.8);
  const filter =
    boundedHue === 0 && boundedSaturation === 1 && boundedBrightness === 1
      ? undefined
      : `hue-rotate(${boundedHue}deg) saturate(${boundedSaturation}) brightness(${boundedBrightness})`;

  return (
    <div
      className={["text-path-study", `text-path-study--${safeMode}`, className]
        .filter(Boolean)
        .join(" ")}
      data-mode={safeMode}
      style={{
        opacity: boundedOpacity,
        filter,
        width: "100%",
        height: "100%",
        ...style,
      }}
    >
      <iframe
        className="text-path-study-frame"
        data-mode={safeMode}
        title="Globe interactive canvas study"
        sandbox="allow-scripts"
        srcDoc={document}
        style={{
          width: "100%",
          height: "100%",
          border: "none",
          display: "block",
          transform: boundedScale === 1 ? undefined : `scale(${boundedScale})`,
        }}
      />
    </div>
  );
}
