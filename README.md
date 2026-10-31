# endstone-chaostools

An [Endstone](https://github.com/EndstoneMC/endstone) plugin for Minecraft Bedrock servers that adds floating texts you move with your crosshair, plus portals and signs that teleport players or send them to another server.

Tested with Bedrock Dedicated Server 1.26.60 and Endstone 0.11.15.

## Install

Download the wheel from the [releases page](https://github.com/Felix-AI-Hub/endstone-chaostools/releases), put it in your server's `plugins/` folder and restart the server.

## Floating texts

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

Texts exist only on the clients. The server sends a display packet and never simulates an entity for them.

## Portals and signs

| Command | What it does |
|---|---|
| `/portal create <name> [radius]` | Creates a portal where you stand. The default radius is 1.5. |
| `/portal target <name>` | Makes your current position the destination. |
| `/portal server <name> <host> [port]` | Sends players to another server. |
| `/portal sign <name>` | Links the next block you right-click, such as a sign. |
| `/portal list` | Lists all portals. |
| `/portal remove <name>` | Removes a portal. |

A Bedrock server loads a single world, so a separate world means a separate server that you link with `/portal server`. Inventories are not carried across.

All commands require the `chaostools.command` permission, which operators have by default.

## Compatibility

The packets are written by hand for protocol 2225, so a new Minecraft version can break floating texts. Since 26.60, each metadata entry writes its value type twice, and older versions will not accept that format.

## Build

```sh
pip install build
python -m build --wheel
```

## License

[MIT](LICENSE)
