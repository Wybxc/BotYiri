import asyncio
from pathlib import Path
from importlib import import_module
from bot import BotYiri

async def load_plugins(bot: BotYiri):
    plugins_path = Path('plugins')
    tasks = []
    for plugin in plugins_path.iterdir():
        if plugin.is_dir() and (plugin / '__init__.py').is_file():
            plugin = import_module('.'.join(plugin.parts))
            if plugin.ENABLED:
                tasks.append(asyncio.create_task(plugin.init(bot)))
    for task in tasks:
        await task
