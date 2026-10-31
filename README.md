# endstone-chaostools

Four independent [Endstone](https://github.com/EndstoneMC/endstone) plugins for Minecraft Bedrock servers. Install only the ones you need.

| Plugin | What it adds |
|---|---|
| [ChaosTexts](#chaostexts) | Floating texts that you move with your crosshair |
| [ChaosPortals](#chaosportals) | Portals and signs that teleport players or send them to another server |
| [ChaosRanks](#chaosranks) | Permission groups with inheritance and name prefixes |
| [ChaosDashboard](#chaosdashboard) | Local web page for managing the server |

Tested with Bedrock Dedicated Server 1.26.60 and Endstone 0.11.15.

## Install

Download the wheels you want from the [releases page](https://github.com/Felix-AI-Hub/endstone-chaostools/releases), put them in your server's `plugins/` folder and restart the server.

## ChaosTexts

| Command | What it does |
|---|---|
| `/ft create <text>` | Creates a text above you. Use `\|` for a line break. |
| `/ft move [id]` | Picks up the text you look at, or the one with this id. It follows your crosshair. |
| Sneak | Places the text you are moving. |
| `/ft drop` | Places it as well. |
| `/ft dist <blocks>` | Sets the distance while moving, from 1 to 64. |
| `/ft edit <id> <text>` | Changes a text. |
| `/ft remove [id]` | Removes the text you look at, or the one with this id. |
| `/ft list` | Lists all texts with their ids. |

Requires `chaostexts.command`. Texts exist only on the clients: the server sends a display packet and never simulates an entity for them.

The packets are written by hand for protocol 2225, so a new Minecraft version can break this plugin. Since 26.60, each metadata entry writes its value type twice, and older versions will not accept that format.

## ChaosPortals

| Command | What it does |
|---|---|
| `/portal create <name> [radius]` | Creates a portal where you stand. The default radius is 1.5. |
| `/portal target <name>` | Makes your current position the destination. |
| `/portal server <name> <host> [port]` | Sends players to another server. |
| `/portal sign <name>` | Links the next block you right-click, such as a sign. |
| `/portal list` | Lists all portals. |
| `/portal remove <name>` | Removes a portal. |

Requires `chaosportals.command`. Inventories are not carried across servers.

## ChaosRanks

| Command | What it does |
|---|---|
| `/rank list` | Lists all ranks. |
| `/rank info [player]` | Shows a player's rank and permissions. |
| `/rank perms [filter]` | Lists the permissions that exist on this server. |
| `/rank create <rank>` | Creates a rank. |
| `/rank delete <rank>` | Deletes a rank. |
| `/rank default <rank>` | Sets the rank for players without one. |
| `/rank set <player> <rank>` | Gives a player a rank. |
| `/rank unset <player>` | Returns a player to the default rank. |
| `/rank perm <rank> <permission> [true\|false]` | Grants or denies a permission. |
| `/rank unperm <rank> <permission>` | Removes a permission entry. |
| `/rank inherit <rank> <parent>` | Makes a rank inherit from another one. |
| `/rank prefix <rank> [text]` | Sets the prefix shown in chat and above the name. |

Requires `chaosranks.command`. Every plugin's permission is for operators by default. All permissions on your server are also written to `plugins/chaosranks/known-permissions.txt`.

Vanilla commands use names like `minecraft.command.kick`. With `allow-cheats=false`, the game can still refuse cheat commands for a player who has the permission.

## ChaosDashboard

A web page that shows players, floating texts, portals and ranks, and lets you kick players, change ranks and run console commands. It works with whichever of the other plugins you have installed.

The first start creates `plugins/chaosdashboard/settings.json` with the port (8099 by default) and a random password in `token`. The server must be able to receive that port, so on a hosted panel add it as an extra allocation.

Anyone with the password can run console commands, and the page uses plain HTTP. Keep it on your local network and don't forward the port.

## Build

Python 3.11 or later is enough:

```sh
python build.py
```

The wheels end up in `dist/`.

## License

[MIT](LICENSE)
