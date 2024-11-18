import discord
from discord.ext import commands, pages


class MultiPage(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.pages = []

    def get_pages(self):
        return self.pages
    
    def set_pages(self, pages):
        self.pages = pages

    async def paginate(self, ctx: discord.ApplicationContext):
        """Demonstrates using emojis for the paginator buttons instead of labels."""
        page_buttons = [
            pages.PaginatorButton(
                "first", emoji="⏪", style=discord.ButtonStyle.green
            ),
            pages.PaginatorButton("prev", emoji="⬅", style=discord.ButtonStyle.green),
            pages.PaginatorButton(
                "page_indicator", style=discord.ButtonStyle.gray, disabled=True
            ),
            pages.PaginatorButton("next", emoji="➡", style=discord.ButtonStyle.green),
            pages.PaginatorButton("last", emoji="⏩", style=discord.ButtonStyle.green),
        ]
        paginator = pages.Paginator(
            pages=self.get_pages(),
            show_disabled=True,
            show_indicator=True,
            use_default_buttons=False,
            custom_buttons=page_buttons,
            loop_pages=True,
            disable_on_timeout=True, 
            timeout=3600
        )
        await paginator.respond(ctx.interaction, ephemeral=False)