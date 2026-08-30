import GlobeStudy, { type GlobeStudyProps } from "@/components/ui/globe-study";

const settings = {
  mode: "dark",
  scale: 1,
  opacity: 1,
  hue: 0,
  saturation: 1,
  brightness: 1,
} as const satisfies GlobeStudyProps;

export default function GlobeStudyDemo(props: Partial<typeof settings>) {
  const s = { ...settings, ...props };
  return (
    <div className="h-screen w-full">
      <GlobeStudy {...s} />
    </div>
  );
}
