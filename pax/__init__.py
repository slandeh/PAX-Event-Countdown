from .pax import PAXCountdown

async def setup(bot):
    await bot.add_cog(PAXCountdown(bot))
