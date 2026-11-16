import os
import re
import discord
import yt_dlp

# Konfigurasi Bot
TOKEN = os.getenv("DISCORD_TOKEN")
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID", 0))

intents = discord.Intents.default()
intents.message_content = True
bot = discord.Client(intents=intents)

# Konfigurasi yt-dlp yang fleksibel untuk berbagai format video/platform
YDL_OPTIONS = {
    'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
    'noplaylist': True,
    'extract_flat': False,
    'cookiefile': 'cookies.txt' if os.path.exists('cookies.txt') else None,
}

@bot.event
async def on_ready():
    print(f"=== BOT MULTI-PLATFORM STABLE V4 ===")
    print(f"Bot masuk sebagai {bot.user} (ID: {bot.user.id})")

async def send_log(guild, user, action, details):
    """Fungsi helper untuk mengirim log aktivitas ke channel khusus"""
    if LOG_CHANNEL_ID == 0:
        return
    
    channel = bot.get_channel(LOG_CHANNEL_ID)
    if channel:
        embed = discord.Embed(
            title="📊 Bot Activity Log",
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(name="Pengguna", value=f"{user} (`{user.id}`)", inline=False)
        embed.add_field(name="Server", value=f"{guild.name if guild else 'Direct Message'}", inline=False)
        embed.add_field(name="Aktivitas", value=action, inline=False)
        embed.add_field(name="Detail", value=details, inline=False)
        await channel.send(embed=embed)

@bot.event
async def on_message(message):
    # Abaikan pesan dari bot sendiri atau bot lain agar tidak terjadi loop
    if message.author.bot:
        return

    # Cari URL (http:// atau https://) di dalam pesan yang dikirim
    url_match = re.search(r'(https?://[^\s]+)', message.content)
    if not url_match:
        return

    url = url_match.group(0)
    msg = await message.reply("⏳ Sedang memproses video, mohon tunggu...")

    try:
        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            info = ydl.extract_info(url, download=False)
            video_title = info.get('title', 'Video')

        await msg.edit(content=f"✅ Berhasil memproses: **{video_title}**\n🔗 {url}")

        # Kirim log aktivitas sukses ke Log Channel
        await send_log(message.guild, message.author, "Download Video", f"Judul: {video_title}\nURL: {url}")

    except Exception as e:
        await msg.edit(content="❌ Terjadi kesalahan saat memproses video.")
        print(f"[ERROR] Terjadi kesalahan: {e}")

        # Kirim log error ke Log Channel
        await send_log(message.guild, message.author, "Error Download", f"URL: {url}\nError: `{e}`")

# Jalankan bot
if __name__ == "__main__":
    bot.run(TOKEN)