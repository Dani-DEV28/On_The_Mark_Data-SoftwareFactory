# Gemini 4 (Google Gemma 3 27B — proxy for Gemini 4 on local hardware)

## Overview
- **Source:** HuggingFace `google/gemma-3-27b-it`
- **Quantization:** Q8_0 GGUF (recommended for GB10)
- **Parameters:** 27B
- **Context:** 32K
- **License:** Gemma Terms of Use

## Assigned Roles
- Tech Lead
- Product Manager
- Technical Project Manager
- Docs Engineer

## Download
```bash
# Via HuggingFace CLI
huggingface-cli download google/gemma-3-27b-it-GGUF/gemma-3-27b-it-Q8_0.gguf \
  --local-dir models/gemini-4/

# Or via curl
curl -L "https://huggingface.co/google/gemma-3-27b-it-GGUF/resolve/main/gemma-3-27b-it-Q8_0.gguf" \
  -o models/gemini-4/gemma-3-27b-it-Q8_0.gguf
```

## Why This Model
- Strong reasoning and structured output
- Excellent at decomposition and AC writing
- Good documentation generation
- Fast enough for PM/TPM coordination roles

## Notes
- Gemma 3 is Google's open model; "Gemini 4" is the project codename for this slot
- If actual Gemini 4 GGUF becomes available, swap the file and update config
- Falls back to Nemotron if unavailable
