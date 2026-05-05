import discord
from discord import app_commands
import os
import uuid

# BIFROST DISCORD MASTER (v16.0)
# Integrated with Discord-Sync Auth Bridge.

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
AUTH_CHANNEL_ID = os.getenv("AUTH_CHANNEL_ID")
GUILD_ID = None # Set to your server ID for instant command sync

# Operator ID of the primary controller
AUTHORIZED_USERS = [] 

class BifrostBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        if GUILD_ID:
            guild = discord.Object(id=GUILD_ID)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
        else:
            await self.tree.sync()

client = BifrostBot()

@client.event
async def on_ready():
    print(f"\n[!] BIFROST DISCORD MASTER ONLINE: {client.user}")
    print(f"[!] SYNCED TO AUTH CHANNEL: {AUTH_CHANNEL_ID}")

@client.tree.command(name="gen", description="Generate a new BIFROST license key")
@app_commands.describe(operator="Operator Name/ID")
async def gen(interaction: discord.Interaction, operator: str = "Clean"):
    if AUTHORIZED_USERS and interaction.user.id not in AUTHORIZED_USERS:
        await interaction.response.send_message("❌ ACCESS DENIED", ephemeral=True)
        return

    if not AUTH_CHANNEL_ID:
        await interaction.response.send_message("❌ ERROR: AUTH_CHANNEL_ID NOT CONFIGURED", ephemeral=True)
        return

    # Generate Secure Key
    new_key = f"Retri-{uuid.uuid4().hex[:8].upper()}-{uuid.uuid4().hex[:8].upper()}"
    
    # Format for API Parsing
    auth_channel = client.get_channel(int(AUTH_CHANNEL_ID))
    if not auth_channel:
        await interaction.response.send_message("❌ ERROR: COULD NOT LOCATE AUTH CHANNEL", ephemeral=True)
        return

    # Post to Vault Channel
    await auth_channel.send(f"KEY: {new_key} | OP: {operator}")

    # Success Response
    embed = discord.Embed(title="⚡ BIFROST LICENSE ACTIVATED", color=0x00d2ff)
    embed.add_field(name="LICENSE KEY", value=f"`{new_key}`", inline=False)
    embed.add_field(name="OPERATOR ID", value=operator, inline=True)
    embed.add_field(name="STATUS", value="ACTIVE", inline=True)
    embed.set_footer(text="BIFROST INDUSTRIAL OSINT & DISRUPTION")
    
    await interaction.response.send_message(embed=embed)

@client.tree.command(name="purge", description="Purge all active keys in the auth channel")
async def purge(interaction: discord.Interaction):
    if AUTHORIZED_USERS and interaction.user.id not in AUTHORIZED_USERS:
        await interaction.response.send_message("❌ UNAUTHORIZED", ephemeral=True)
        return

    auth_channel = client.get_channel(int(AUTH_CHANNEL_ID))
    if auth_channel:
        await interaction.response.defer()
        deleted = await auth_channel.purge(limit=100)
        await interaction.followup.send(f"✅ PURGE COMPLETE: {len(deleted)} LICENSES REVOKED")
    else:
        await interaction.response.send_message("❌ CHANNEL NOT FOUND")

if __name__ == "__main__":
    if not DISCORD_TOKEN:
        print("[!] ERROR: DISCORD_TOKEN NOT FOUND IN ENVIRONMENT")
    else:
        client.run(DISCORD_TOKEN)
