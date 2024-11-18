

from src.const import BOT, TOKEN
from src.discord_bot.paginator import MultiPage

@BOT.event
async def on_ready():
    print("Ready!")
    BOT.add_cog(MultiPage(BOT))

BOT.run(TOKEN)