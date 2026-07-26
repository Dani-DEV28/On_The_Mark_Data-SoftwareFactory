# PREP.md — Night-Before Checklist

Everything that must happen before the hackathon day. Plans + staged artifacts only — no code.

## Hardware

- [ ] GB10 packed and powered
- [ ] MBP packed with charger
- [ ] Power strip
- [ ] USB-C → Ethernet adapter + Ethernet cable
- [ ] USB backup drive (optional)
- [ ] Second person's laptop + accessories confirmed

## Network

- [ ] Pre-generate Tailscale auth key
- [ ] Phone hotspot ready as backup
- [ ] Ethernet Mac ↔ GB10 confirmed working
- [ ] macOS Internet Sharing configured

## Credentials

- [ ] HF token (for model downloads)
- [ ] NGC key (for NVIDIA model pulls — signup can stall, do tonight)
- [ ] Test: `huggingface-cli whoami` succeeds
- [ ] Test: `ngc auth status` succeeds

## Staging

- [ ] Run `./stage-usb.sh` (defaults to `~/hackathon-stage`)
- [ ] Binaries: vLLM, llama-swap, agentgateway
- [ ] Weights: model weight files
- [ ] Repos: kata, openshell-sandbox, etc.
- [ ] Verify: `ls ~/hackathon-stage/binaries/` shows all expected files

## Models

- [ ] Download Gemma 3 27B GGUF (Q8_0)
- [ ] Download Nemotron 3 Super 120B (or 8B variant)
- [ ] Download Qwen 3 32B GGUF (Q8_0)
- [ ] Verify: files exist in `models/` directories
- [ ] Test: `ollama list` shows available models

## Software Stack

- [ ] `nemoclaw --version` or install script staged
- [ ] `openshell --version` or install script staged
- [ ] `openclaw --version` or npm/pip install staged
- [ ] `kata --version` or pip install staged
- [ ] `python3 --version` (3.10+)
- [ ] `git --version`

## Corpus

- [ ] Confirm: `pallets/click` is the default corpus repo
- [ ] Clone to stage: `git clone https://github.com/pallets/click.git stage/repos/click`
- [ ] Verify: `cd stage/repos/click && python -m pytest --co` (collects tests)

## Pair Programming

- [ ] Second person's access confirmed
- [ ] tmate or VS Code Liveshare setup tested
- [ ] Both machines on Tailscale tailnet
- [ ] `ssh` access between machines tested

## Demo Briefs (Pre-Written)

Prepare 5-10 realistic maintenance briefs for `pallets/click`:

1. "Add a `--timeout` flag to Click commands with configurable default"
2. "Fix issue #1234: environment variable override not working on Windows"
3. "Add type hints to the `core.py` module"
4. "Improve error messages for invalid parameter types"
5. "Add a `--version` flag helper to Click groups"
6. "Write integration tests for the `MultiCommand` class"
7. "Refactor `utils.py` to reduce cyclomatic complexity"
8. "Add a `CHANGES.md` file documenting recent API changes"
9. "Fix deprecation warning in Python 3.12 compatibility"
10. "Add a `--verbose` flag that controls logging level"

## Emergency Contacts

- [ ] Fellow competitor contact info
- [ ] Organizer contact info
- [ ] Venue WiFi backup info

## Final Check

- [ ] All staged artifacts on USB/drive
- [ ] Both laptops charged
- [ ] Backup plan documented (Plan B: OpenClaw + openshell-sandbox plugin)
- [ ] `rsync` script ready: `rsync -avz ~/hackathon-stage user@gb10:/home/user/`
- [ ] Sleep.
