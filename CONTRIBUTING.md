# Contributing to Sophia Edge Node

Welcome! This project combines RustChain mining with RetroAchievements gaming rewards. Contributions are welcome.

## Development Setup

```bash
# Clone your fork
git clone https://github.com/MingYu5/sophia-edge-node.git
cd sophia-edge-node

# Install dependencies
sudo ./install.sh

# Test miner directly
python3 rustchain_miner.py --wallet YOUR_WALLET_ADDRESS
```

## Project Structure

| File | Description |
|------|-------------|
| `rustchain_miner.py` | Main mining script |
| `achievement_bridge.py` | RetroAchievements API bridge |
| `proof_of_play.py` | Session tracking & heartbeat |
| `cartridge_wallet.py` | Soulbound relic collector |
| `config.json` | Configuration file |

## Code Style

- Python 3.8+
- 4 spaces indentation
- Max line length: 100
- Run `python3 -m py_compile *.py` before committing

## Pull Request Process

1. Fork the repo
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Test on real hardware (VM detection will penalize weight)
4. Commit with clear messages
5. Open a PR against `Scottcjn/sophia-edge-node:main`

## Hardware Requirements

- Raspberry Pi 4/5 (other ARM boards may work but untested)
- RetroArch or RetroPie installed for achievement tracking
- Network connectivity to RustChain node

## Testing

```bash
# Dry run (no actual mining)
python3 rustchain_miner.py --wallet test --dry-run

# Verify hardware fingerprint
python3 -c "from rustchain_miner import detect_hardware; print(detect_hardware())"
```

## Questions?

- Open an issue for bugs
- Discussions for feature ideas
- Check existing issues before creating new ones

---

**Tip:** This project rewards real hardware. VMs and cloud instances get penalized. Test on actual Raspberry Pi hardware for accurate results.
