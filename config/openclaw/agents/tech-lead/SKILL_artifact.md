# Skill: Artifact Creation

You produce visual HTML documents that demonstrate progress and changes in the repository.

## Triggered By
`sfai create artifact -p "prompt" [-t tag]`

## Inputs
- Current kata board state (open/closed, statuses, cycle times)
- Recent git log from corpus repo
- Corpus diff statistics
- User prompt describing what to visualize

## Output
A self-contained HTML file saved to `evidence/artifacts/<tag>-<timestamp>.html`

## HTML Requirements
- Single file with embedded CSS and JavaScript
- No external CDN, font, or network dependencies
- Dark theme with clear visual hierarchy
- All data includes timestamps and context
- Opens correctly in a browser offline
- Do NOT wrap in markdown code fences — output raw HTML only

## Examples
- Progress dashboard showing kata status distribution
- Git contribution graph for the corpus repo
- Test pass/fail trend visualization
- Architecture diagram of recent changes
