import os
import discord
from discord.ext import commands
import yt_dlp

# Konfigurasi Bot
TOKEN = os.getenv("DISCORD_TOKEN")  # Token bot dari environment variable atau masukkan langsung
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID", 0))  # ID Channel Discord untuk log aktivitas (ubah atau isi di Railway)

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Konfigurasi yt-dlp yang diperbarui untuk mengatasi error bot YouTube & mendukung cookies.txt
YDL_OPTIONS = {
    'format': 'best',
    'noplaylist': True,
    'extract_flat': False,
    # Menggunakan client Android/Web untuk menghindari pembatasan SABR / deteksi bot
    'extractor_args': {
        'youtube': {
            'player-client': ['android', 'web']
        }
    },
    # Jika Anda memiliki file cookies.txt untuk autentikasi akun YouTube, letakkan di folder yang sama
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

@bot.command(name="dl", help="Mengunduh video dari YouTube/platform lain")
async def download_video(ctx, url: str):
    # Kirim respon awal bahwa proses sedang berjalan
    msg = await ctx.send("⏳ Sedang memproses video, mohon tunggu...")
    
    try:
        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            info = ydl.extract_info(url, download=False)
            video_title = info.get('title', 'Video')
            video_url = info.get('url', url)
            
        await msg.edit(content=f"✅ Berhasil memproses: **{video_title}**\n🔗 {url}")
        
        # Kirim log aktivitas ke Log Channel
        await send_log(ctx.guild, ctx.author, "Download Video", f"Judul: {video_title}\nURL: {url}")
        
    py-except Exception as e:
        await msg.edit(content=f"❌ Terjadi kesalahan saat memproses video.")
        print(f"[ERROR] Terjadi kesalahan: {e}")
        
        # Kirim log error ke Log Channel
        await send_log(ctx.guild, ctx.author, "Error Download", f"URL: {url}\nError: `{e}`")

# Jalankan bot
if __name__ == "__main__":
    bot.run(TOKEN)