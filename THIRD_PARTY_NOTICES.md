# Third-party notices

AI Buddy is an independent project. It does not copy code from the projects below. It uses the
Hermes Gadget SDK as an installed tool, and it describes the protocol from that project's public
documentation.

| Project | Licence | How AI Buddy relates to it |
|---|---|---|
| [Hermes Gadget SDK](https://github.com/Adolanium/hermes-gadget-sdk) by Adolanium and contributors | MIT | Used as a tool: its simulator and stand-in Hermes server. Protocol behaviour is taken from its docs. No source copied. |
| [physical-hermes](https://github.com/RegeneratusLabs/physical-hermes) by RegeneratusLabs | See that repository | The inspiration for this project. No code copied. |
| [xiaozhi-esp32](https://github.com/78/xiaozhi-esp32) | See that repository | The firmware the target robot ships with. Referenced only. |
| [Hermes Agent](https://hermes-agent.nousresearch.com) by Nous Research | See that project | The default brain, reached over the gadget protocol. Trademarks belong to Nous Research. |

Python dependencies (installed from PyPI, each under its own licence): websockets, PyYAML, Pillow,
aiohttp, pytest and pytest-asyncio.

If code from any project above is ever copied into this repository, add its licence text and notice
here in the same commit.
