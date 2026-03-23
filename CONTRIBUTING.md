# Contributing to Sophia Edge Node

Thank you for your interest in contributing to Sophia Edge Node! This guide will help you get started.

## Quick Start

1. **Fork** the repository
2. **Clone** your fork locally
3. **Create a branch** for your changes (`git checkout -b feature/my-contribution`)
4. **Make your changes** and test them
5. **Commit** with a clear message
6. **Push** to your fork and open a **Pull Request**

## Development Setup

### Prerequisites

- Raspberry Pi 4 or 5 (recommended) or any ARM-based Linux system
- Python 3.9+
- Git

### Running Locally

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/sophia-edge-node.git
cd sophia-edge-node

# Run the installer (optional, for full setup)
sudo ./install.sh

# Or run individual components for testing
python3 rustchain_miner.py
python3 achievement_bridge.py
python3 proof_of_play.py
```

## Project Structure

```
sophia-edge-node/
├── rustchain_miner.py       # Core mining attestation
├── achievement_bridge.py    # RetroAchievements integration
├── proof_of_play.py         # Gaming session tracking
├── cartridge_wallet.py      # Soulbound cartridge relics
├── community_events.py      # Events and leaderboards
├── game_recommender.py      # Game recommendations
├── hud_overlay.py           # In-game overlay
├── controller_detect.py     # Controller detection
├── daily_digest.py          # Daily summary reports
├── leaderboard.py           # Community rankings
├── config.json              # Configuration file
├── install.sh               # Installation script
└── sounds/                  # Audio assets
```

## Types of Contributions

### Code
- Bug fixes and feature implementations
- New game system support
- Performance improvements
- Anti-cheat enhancements

### Documentation
- README improvements
- Code comments
- Usage examples
- Tutorials

### Testing
- Test on different Raspberry Pi models
- Test on other ARM SBCs
- Edge case handling
- Game compatibility testing

## Code Style

- **Python 3.9+** — Follow PEP 8 style guide
- **Clear function names** — Describe what the function does
- **Docstrings** — Document parameters and return values
- **Error handling** — Graceful failures with helpful messages

### Example

```python
def calculate_achievement_reward(points: int, rarity: float) -> float:
    """
    Calculate RTC reward for an achievement.
    
    Args:
        points: Achievement point value
        rarity: Rarity multiplier (1.0-3.0)
        
    Returns:
        float: RTC reward amount
    """
    base = points * 0.00001
    return base * rarity
```

## Pull Request Guidelines

1. **One feature per PR** — Keep changes focused
2. **Test your changes** — Run the affected components
3. **Update documentation** — If you add features, document them
4. **Follow the existing style** — Match the codebase conventions

### PR Title Format

Use conventional commits:
- `feat:` — New feature
- `fix:` — Bug fix
- `docs:` — Documentation changes
- `refactor:` — Code refactoring
- `test:` — Adding tests

## Reporting Issues

1. Check if the issue has already been reported
2. Use a clear and descriptive title
3. Include your hardware (Pi model, OS version)
4. Provide steps to reproduce
5. Include relevant log output

## Getting Help

- Open an issue for bugs or feature requests
- Check existing issues before creating new ones
- Join the [Discord](https://discord.gg/VqVVS2CW9Q)

## License

By contributing, you agree that your contributions will be licensed under the MIT License.