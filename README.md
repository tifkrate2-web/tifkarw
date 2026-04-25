# Telegram Group Assistant Bot

An async Python Telegram bot for managing groups: welcome messages, moderation, anti-spam,
rules, saved notes, and optional AI Q&A.

Built with [`python-telegram-bot`](https://github.com/python-telegram-bot/python-telegram-bot)
v21 and SQLite. Designed to be friendly to **Termux** on Android — no native deps required.

## Features

- **Welcome / Goodbye** — customizable per group with `{user}` and `{chat}` placeholders.
- **Moderation** — `/ban`, `/kick`, `/mute` (with duration), `/unmute`, `/warn`, `/warns`,
  `/resetwarns`, `/setwarnlimit`, `/purge`, `/pin`, `/unpin`, `/promote`, `/demote`.
- **Anti-spam** — anti-flood (per-user rate limiting), block links, block forwards.
- **Rules** — `/setrules`, `/rules`, `/clearrules`.
- **Notes** — `/save name content`, `/get name` (or `#name`), `/notes`, `/clear name`.
- **Info** — `/id`, `/info` (user info, IDs).
- **AI Q&A (optional)** — `/ask <question>` via OpenAI (only enabled if `OPENAI_API_KEY` is set).

Send `/help` to the bot for a full command list.

## Quick start

### 1. Create a bot
1. Open Telegram and message [@BotFather](https://t.me/BotFather).
2. Run `/newbot` and follow the prompts. Save the bot token.
3. Run `/setprivacy` → choose your bot → **Disable** privacy mode (so the bot can read group
   messages for anti-spam). This step is required for moderation features to work properly.

### 2. Run on Termux (Android)

```bash
pkg update && pkg upgrade -y
pkg install -y python git
git clone https://github.com/tifkrate2-web/telegram-group-assistant-bot
cd telegram-group-assistant-bot
pip install -r requirements.txt
cp .env.example .env
# Edit .env and set BOT_TOKEN. nano is available via: pkg install nano
nano .env
python -m bot
```

To keep the bot running after closing Termux, acquire a wakelock:
```bash
termux-wake-lock
python -m bot
```

Or use `tmux` (`pkg install tmux`) to detach the session.

### 3. Run on a desktop / VPS

```bash
git clone https://github.com/tifkrate2-web/telegram-group-assistant-bot
cd telegram-group-assistant-bot
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# fill in BOT_TOKEN
python -m bot
```

For a long-running deployment, use `systemd`, `supervisor`, or `tmux`/`screen`.

## Configuration

All config is via environment variables (or a `.env` file). See `.env.example`.

| Variable          | Required | Default       | Description                                                |
|-------------------|----------|---------------|------------------------------------------------------------|
| `BOT_TOKEN`       | yes      | —             | Telegram bot token from @BotFather.                        |
| `OWNER_IDS`       | no       | (empty)       | Comma-separated Telegram user IDs with global owner perms. |
| `DB_PATH`         | no       | `bot.db`      | Path to the SQLite database file.                          |
| `OPENAI_API_KEY`  | no       | (empty)       | Enables `/ask`. Leave empty to disable AI features.        |
| `OPENAI_MODEL`    | no       | `gpt-4o-mini` | Model used for `/ask`.                                     |
| `LOG_LEVEL`       | no       | `INFO`        | One of `DEBUG`, `INFO`, `WARNING`, `ERROR`.                |

## Add the bot to a group

1. Add your bot to the group.
2. Promote it to **Administrator** with permissions:
   - Delete messages
   - Ban / restrict members
   - Pin messages
   - (optional) Add new admins — needed for `/promote` / `/demote`
3. Send `/help` in the group.

## Commands cheat sheet

| Category   | Commands                                                                                    |
|------------|---------------------------------------------------------------------------------------------|
| Welcome    | `/setwelcome`, `/setgoodbye`, `/clearwelcome`, `/cleargoodbye`                              |
| Moderation | `/ban`, `/kick`, `/mute`, `/unmute`, `/warn`, `/warns`, `/resetwarns`, `/setwarnlimit`      |
| Cleanup    | `/purge` (reply to the first message), `/pin`, `/unpin`                                     |
| Roles      | `/promote`, `/demote`                                                                       |
| Anti-spam  | `/antiflood on/off/<limit> <window>`, `/blocklinks on/off`, `/blockforwards on/off`         |
| Rules      | `/setrules`, `/rules`, `/clearrules`                                                        |
| Notes      | `/save <name> <content>`, `/get <name>` (or `#name`), `/notes`, `/clear <name>`             |
| Info       | `/id`, `/info`, `/start`, `/help`                                                           |
| AI         | `/ask <question>`                                                                           |

## Project layout

```
bot/
├── __main__.py        # entry point (python -m bot)
├── config.py          # env-var configuration
├── db/store.py        # SQLite store
├── handlers/
│   ├── start.py       # /start, /help
│   ├── welcome.py     # welcome/goodbye + chat_member events
│   ├── moderation.py  # ban/kick/mute/warn/purge/pin/promote
│   ├── antispam.py    # anti-flood, block links/forwards
│   ├── rules.py       # /setrules, /rules
│   ├── notes.py       # /save, /get, #hashtag lookup
│   ├── info.py        # /id, /info
│   └── ai.py          # /ask via OpenAI
└── utils/permissions.py
```

## Development

```bash
pip install -r requirements.txt
pip install ruff
ruff check .
python -m compileall bot
```

## License

MIT — see [LICENSE](LICENSE).
