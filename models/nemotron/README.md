# NVIDIA Nemotron 3 Super 120B

## Overview
- **Source:** NVIDIA NGC / Ollama
- **Parameters:** 120B
- **Context:** 32K
- **License:** NVIDIA Open Model License

## Assigned Roles
- Software Architect
- DevOps + QA Engineer

## Download
```bash
# Via Ollama
ollama pull nemotron:latest

# Via NGC
ngc model download nvidia/nemotron-3-super-120b

# Via HuggingFace
huggingface-cli download nvidia/nemotron-3-super-120b \
  --local-dir models/nemotron/
```

## Why This Model
- Deep technical reasoning
- Strong at system-level thinking
- Excellent test coverage analysis
- Best at architectural fitness functions

## Notes
- This is the largest model in the stack — primary compute consumer
- If 120B is too large for concurrent loading, use the 8B variant for lighter roles
- Falls back to Gemini 4 (Gemma 3 27B) if unavailable
