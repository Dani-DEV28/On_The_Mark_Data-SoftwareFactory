---
name: create-artifact
description: Create a self-contained HTML artifact (dashboard, report, visualization) from a prompt and available context. Use whenever the user asks for an artifact, dashboard, progress view, status page, or any visual HTML document.
---

# Create Artifact

You are producing a **self-contained HTML document** the user can open directly in a
browser or share with stakeholders. This is a core Tech Lead responsibility.

## Hard requirements

- One single `.html` file, starting with `<!doctype html>`.
- **Fully self-contained**: all CSS and JS inline. No external CDNs, no network
  requests, no remote fonts or images. It must render correctly offline.
- **Dark theme** by default: dark background (#0d1117-ish), light text, one green
  accent (#76b900). Clean typography, generous spacing, system font stack.
- Responsive: no horizontal page scroll; wide tables/diagrams scroll inside their
  own container.

## Procedure

1. Gather context for the content:
   - The user's prompt (what they want visualized).
   - Any files in the workspace they reference.
   - If they ask about factory/board state, use whatever board or status
     information is available in the conversation or workspace — do not invent
     numbers; omit what you don't know rather than fabricate.
2. Write the complete HTML file to the workspace:
   - Path: `artifacts/<tag>-<YYYYMMDD-HHMMSS>.html` (create the `artifacts/`
     directory if needed). Derive `<tag>` from the request (kebab-case, short).
3. Reply with:
   - The full sandbox path of the file.
   - A one-line summary of what it shows.
   - How to retrieve it from the host:
     `nemoclaw local-pm-os-agent download <sandbox-path> <host-dest>`

## Style guidance

- Lead with the headline fact; support with structure (cards, tables, timelines).
- Use real data only. If a metric is unavailable, leave it out.
- Keep it to one screen-ish of content unless the request demands more.
