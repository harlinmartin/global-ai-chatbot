"use client";
import { motion, AnimatePresence } from "framer-motion";
import type { StatusStep } from "@/hooks/useStream";

const STEP_ICONS: Record<string, string> = {
  thinking: "🔍",
  generating: "🧠",
  searching: "📚",
  tool_exec: "⚙️",
};

interface Props {
  steps: StatusStep[];
  visible: boolean;
}

export default function AIProcessPanel({ steps, visible }: Props) {
  return (
    <AnimatePresence>
      {visible && steps.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 8, scale: 0.97 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 8, scale: 0.97 }}
          transition={{ duration: 0.2 }}
          className="mx-4 mb-2 rounded-xl border overflow-hidden"
          style={{
            background: "rgba(18,18,22,0.9)",
            borderColor: "var(--border)",
            backdropFilter: "blur(12px)",
          }}
        >
          <div className="px-4 py-3 flex flex-col gap-2">
            {steps.map((s) => (
              <div key={s.step} className="flex items-center gap-3">
                {/* Icon */}
                <span className="text-sm w-5 text-center">
                  {STEP_ICONS[s.step] ?? "⚙️"}
                </span>

                {/* Label */}
                <span
                  className="text-sm flex-1"
                  style={{
                    color:
                      s.state === "done"
                        ? "var(--text-muted)"
                        : "var(--text-secondary)",
                  }}
                >
                  {s.label}
                </span>

                {/* Status indicator */}
                {s.state === "active" && (
                  <motion.span
                    animate={{ opacity: [1, 0.3, 1] }}
                    transition={{ duration: 1, repeat: Infinity }}
                    className="w-2 h-2 rounded-full"
                    style={{ background: "var(--accent)" }}
                  />
                )}
                {s.state === "done" && (
                  <motion.span
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    className="text-xs"
                    style={{ color: "var(--success)" }}
                  >
                    ✓
                  </motion.span>
                )}
              </div>
            ))}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
