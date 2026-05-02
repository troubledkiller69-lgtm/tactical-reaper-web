import discord
from discord import app_commands
import os
import uuid
from supabase import create_client, Client

# --- CONFIG ---
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = None 

# --- SUPABASE CONFIG ---
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://smxpzldbxewcgrakaqhn.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "sb_publishable_QviDYLWIVjVJl4N01Bqaug_ZgkNHcde")

# --- AUTHORIZATION ---
# Replace with the Discord User ID of the bot admin (or leave blank to allow anyone to generate keys initially)
AUTHORIZED_USERS = []

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

class EniDiscordBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        if GUILD_ID:
            guild = discord.Object(id=GUILD_ID)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
        else:
            await self.tree.sync()

client = EniDiscordBot()

@client.event
async def on_ready():
    print(f"[!] Discord Master is online as {client.user}")

@client.tree.command(name="genkey", description="Generate a new Tactical Reaper cloud access key")
@app_commands.describe(hours="Duration in hours (default 24)")
async def genkey(interaction: discord.Interaction, hours: int = 24):
    if AUTHORIZED_USERS and interaction.user.id not in AUTHORIZED_USERS:
        await interaction.response.send_message("❌ Unauthorized to generate keys.", ephemeral=True)
        return

    new_key = f"Retri-{uuid.uuid4().hex[:8].upper()}-{uuid.uuid4().hex[:8].upper()}"
    data = {
        "key": new_key,
        "duration_hours": hours,
        "status": "active"
    }
    
    try:
        supabase.table("keys").insert(data).execute()
        
        embed = discord.Embed(title="🚀 New Cloud License Generated", color=discord.Color.magenta())
        embed.add_field(name="Key", value=f"`{new_key}`", inline=False)
        embed.add_field(name="Duration", value=f"{hours} hours", inline=True)
        embed.set_footer(text="Tactical Reaper Cloud Engine")
        
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message(f"❌ Database Error: {e}", ephemeral=True)

@client.tree.command(name="stats", description="View cloud licensing statistics")
async def stats(interaction: discord.Interaction):
    try:
        response = supabase.table("keys").select("*", count="exact").execute()
        total_keys = response.count if response.count is not None else 0
        
        active_response = supabase.table("keys").select("*", count="exact").eq("status", "active").execute()
        active_keys = active_response.count if active_response.count is not None else 0
        
        embed = discord.Embed(title="📊 Cloud System Statistics", color=discord.Color.cyan())
        embed.add_field(name="Total Keys Created", value=str(total_keys), inline=True)
        embed.add_field(name="Active Keys", value=str(active_keys), inline=True)
        embed.set_footer(text="Tactical Reaper Cloud Engine")
        
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message(f"❌ Database Error: {e}", ephemeral=True)

if __name__ == "__main__":
    if not DISCORD_TOKEN:
        print("[!] Error: DISCORD_TOKEN environment variable not set.")
    else:
        client.run(DISCORD_TOKEN)
