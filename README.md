# Sophia Edge Node

Mine RTC while playing retro games on your Raspberry Pi.

A lightweight edge node for the [RustChain](https://rustchain.org) network that combines hardware attestation mining with [RetroAchievements](https://retroachievements.org) reward integration. Earn RTC tokens for unlocking achievements in classic games.

## Quick Install

```bash
git clone https://github.com/Scottcjn/sophia-edge-node.git
cd sophia-edge-node
sudo ./install.sh
```

The installer will prompt for your RTC wallet ID and (optionally) RetroAchievements credentials.

## How It Works

- **Mining**: Your Pi submits hardware attestation to the RustChain network every 10 minutes. ARM devices earn 0.0005x weight -- small but honest. Real hardware, real attestation.
- **Achievements**: The bridge polls RetroAchievements.org for your recently unlocked achievements and converts them into RTC reward claims, classified by rarity tier.
- **Anti-cheat**: Hardware fingerprint checks (clock drift, thermal analysis, VM detection) ensure only real Raspberry Pi hardware participates.

## Achievement Rewards

| Tier | Points | RTC per Achievement |
|------|--------|---------------------|
| Common | 1-5 | 0.00005 |
| Uncommon | 5-10 | 0.0002 |
| Rare | 10-25 | 0.0005 |
| Ultra Rare | 25-50 | 0.001 |
| Legendary | 50-100 | 0.005 |
| Game Mastery | 100% | 0.01 bonus |

Hardcore mode achievements earn **2x** multiplier. Daily cap: 0.05 RTC.

## Configuration

Edit `/opt/sophia-edge-node/config.json` or use environment variables:

| Variable | Purpose |
|----------|---------|
| `SOPHIA_WALLET` | RTC wallet ID |
| `SOPHIA_NODE_URL` | RustChain node URL |
| `RA_USERNAME` | RetroAchievements username |
| `RA_API_KEY` | RetroAchievements API key |

## Manage Services

```bash
sudo systemctl status sophia-miner
sudo systemctl status sophia-achievements
sudo journalctl -u sophia-miner -f
sudo journalctl -u sophia-achievements -f
```

## Supported Hardware

- Raspberry Pi 5 (BCM2712)
- Raspberry Pi 4 (BCM2711)
- Other ARM SBCs (aarch64/armv7l) -- should work, not guaranteed

## Requirements

- Raspberry Pi OS (64-bit recommended) or any Debian-based ARM Linux
- Python 3.9+
- Network access to RustChain node
- [RetroAchievements](https://retroachievements.org) account (free, for achievement rewards)

## Links

- [RustChain](https://rustchain.org) -- The network
- [BoTTube](https://bottube.ai) -- AI video platform
- [RetroAchievements](https://retroachievements.org) -- Track your retro gaming progress
- [Elyan Labs](https://github.com/Scottcjn) -- Who built this

## License

MIT
