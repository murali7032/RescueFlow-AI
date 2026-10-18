import React from "react";

type ExplanationBlock =
  | { kind: "heading"; text: string }
  | { kind: "paragraph"; text: string }
  | { kind: "list"; items: string[] };

function normalizeExplanation(value: string): string[] {
  return value
    .replace(/\\([*#])/g, "$1")
    .replace(/\r\n?/g, "\n")
    .replace(/\s+(#{1,3}\s+)/g, "\n\n$1")
    .replace(/(#{1,3}\s+(?:Top Pending Offer|What Happens Next|Your Next Step|Current Status))\s*/gi, "$1\n")
    .replace(/\s+\*\s+(?=\*\*[^*]+:\*\*)/g, "\n* ")
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);
}

function parseBlocks(lines: string[]): ExplanationBlock[] {
  const blocks: ExplanationBlock[] = [];
  for (const line of lines) {
    const heading = line.match(/^#{1,3}\s+(.+)$/);
    if (heading) {
      blocks.push({ kind: "heading", text: heading[1].trim() });
      continue;
    }
    const bullet = line.match(/^(?:[-*•]|\d+[.)])\s+(.+)$/);
    if (bullet) {
      const item = bullet[1].trim();
      const previous = blocks[blocks.length - 1];
      if (previous?.kind === "list") previous.items.push(item);
      else blocks.push({ kind: "list", items: [item] });
      continue;
    }
    blocks.push({ kind: "paragraph", text: line });
  }
  return blocks;
}

function InlineFormatting({ text }: { text: string }) {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return (
    <>
      {parts.map((part, index) =>
        part.startsWith("**") && part.endsWith("**") ? (
          <strong key={index}>{part.slice(2, -2)}</strong>
        ) : (
          <React.Fragment key={index}>{part}</React.Fragment>
        ),
      )}
    </>
  );
}

/** Render Gemini's plain-text/Markdown response as safe, readable React content. */
export function AIExplanation({ text }: { text: string }) {
  const blocks = parseBlocks(normalizeExplanation(text));
  return (
    <div className="ai-explanation">
      {blocks.map((block, index) => {
        if (block.kind === "heading") {
          return <h3 key={index}>{block.text}</h3>;
        }
        if (block.kind === "list") {
          return (
            <ul key={index}>
              {block.items.map((item, itemIndex) => (
                <li key={itemIndex}><InlineFormatting text={item} /></li>
              ))}
            </ul>
          );
        }
        return <p key={index}><InlineFormatting text={block.text} /></p>;
      })}
    </div>
  );
}
