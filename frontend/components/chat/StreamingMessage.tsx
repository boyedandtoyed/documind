'use client';

interface StreamingMessageProps {
  content: string;
}

export function StreamingMessage({ content }: StreamingMessageProps) {
  return (
    <div className="text-sm leading-relaxed text-[#F1F5F9]">
      {content ? (
        <span className="whitespace-pre-wrap">
          {content}
          <span className="ml-0.5 inline-block h-4 w-0.5 animate-pulse bg-indigo-400" />
        </span>
      ) : (
        <span className="flex items-center gap-1.5 text-[#64748B]">
          <span className="flex gap-1">
            {[0, 0.15, 0.3].map((delay) => (
              <span
                key={delay}
                className="inline-block h-1.5 w-1.5 rounded-full bg-indigo-500 opacity-70"
                style={{ animation: `pulse 1.2s ease-in-out ${delay}s infinite` }}
              />
            ))}
          </span>
          Thinking…
        </span>
      )}
    </div>
  );
}
