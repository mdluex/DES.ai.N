"""Example custom tool plugin for DES.ai.N."""


async def echo(message: str = "hello") -> dict:
    return {"echo": message}


PLUGIN = {
    "name": "example",
    "tools": [
        {
            "name": "example_echo",
            "description": "Echo a message. Demonstrates the DES.ai.N plugin system.",
            "handler": echo,
            "input_schema": {
                "type": "object",
                "properties": {
                    "message": {"type": "string", "description": "Text to echo"},
                },
                "required": ["message"],
            },
        }
    ],
}
