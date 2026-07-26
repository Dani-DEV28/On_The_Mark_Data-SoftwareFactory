# Qwen 3.6

## Overview
- **Source:** HuggingFace `Qwen/Qwen3-32B`
- **Quantization:** Q8_0 GGUF (recommended for GB10)
- **Parameters:** 32B
- **Context:** 32K
- **License:** Apache 2.0 (Qwen3)

## Assigned Roles
- Software Implementers (code generation)

## Download
```bash
# Via HuggingFace CLI
huggingface-cli download Qwen/Qwen3-32B-GGUF/qwen3-32b-Q8_0.gguf \
  --local-dir models/qwen3.6/

# Or via curl
curl -L "https://huggingface.co/Qwen/Qwen3-32B-GGUF/resolve/main/qwen3-32b-Q8_0.gguf" \
  -o models/qwen3.6/qwen3-32b-Q8_0.gguf
```

## Why This Model
- Excellent code generation across languages
- Strong instruction following
- Good at translating design notes into implementation
- Fast enough for iterative implementer loops

## Notes
- Qwen 3.6 is the project codename for this slot
- If actual Qwen 3.6 GGUF becomes available, swap the file and update config
- Falls back to Nemotron if unavailable
- Multiple implementer agents can share this model concurrently via llama-swap
