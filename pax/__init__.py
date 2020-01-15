from .pax import PAXCountdown

def setup(bot):
    bot.add_cog(PAXCountdown(bot))
