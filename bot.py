import os
import re
import json
import discord
from discord.ext import commands
import yt_dlp
import requests

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

MULTI_PLATFORM_REGEX = re.compile(
    r"https?://(?:www\.)?"
    r"(?:(?:"
    r"tiktok\.com/\S+|"
    r"(?:m|vm|vt)\.tiktok\.com/\S+|"
    r"instagram\.com/(?:p|reel|reels)/\S+|"
    r"youtu\.?be/(?:watch\?v=|shorts/)?[a-zA-Z0-9_-]+|"
    r"youtube\.com/(?:watch\?v=|shorts/|embed/)[a-zA-Z0-9_-]+|"
    r"(?:twitter|x)\.com/\S+"
    r"))"
)

def upload_to_cloud(file_path):
    url = "https://uguu.se/upload"
    try:
        with open(file_path, "rb") as f:
            files = {"files[]": f}
            response = requests.post(url, files=files, timeout=60)
            print(f"[UGUU] Status: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    if data.get("success") and data.get("files"):
                        return data["files"][0]["url"].strip()
                except json.JSONDecodeError:
                    if "uguu.se" in response.text:
                        return response.text.strip()
    except Exception as e:
        print(f"[UGUU] Gagal upload: {e}")
    return None

@bot.event
async def on_ready():
    print("=== BOT MULTI-PLATFORM STABLE ===")
    print(f"Bot masuk sebagai {bot.user} (ID: {bot.user.id})")

@bot.event
async def on_message(message):
    if message.author.bot:
        await bot.process_commands(message)
        return

    match = MULTI_PLATFORM_REGEX.search(message.content)
    if match:
        url = match.group(0)

        # Cek jika tautan adalah slideshow foto TikTok
        if "tiktok.com" in url and "/photo/" in url:
            await message.reply("❌ Maaf, tautan tersebut adalah **postingan foto/slideshow TikTok**, bukan video.")
            return

        downloaded_file = None

        async with message.channel.typing():
            try:
                # Konfigurasi yt-dlp yang dioptimalkan untuk server cloud (Railway)
                ydl_opts = {
                    "outtmpl": f"media_{message.id}.%(ext)s",
                    "noplaylist": True,
                    "quiet": True,
                    "format": "best[ext=mp4]/best",
                    "geo_bypass": True,
                    "nocheckcertificate": True,
                    "extractor_args": {
                        "youtube": {
                            "player_client": ["android", "web"]
                        }
                    },
                    "http_headers": {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                        "Accept-Language": "en-US,en;q=0.9",
                    }
                }

                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    downloaded_file = ydl.prepare_filename(info)
                    if not os.path.exists(downloaded_file):
                        base, _ = os.path.splitext(downloaded_file)
                        for ext in ['.mp4', '.mkv', '.webm', '.mov']:
                            if os.path.exists(base + ext):
                                downloaded_file = base + ext
                                break

                    uploader = (
                        info.get("uploader")
                        or info.get("channel")
                        or info.get("creator")
                        or "Kreator"
                    )
                    description = (
                        info.get("description")
                        or info.get("title")
                        or "Video Media Sosial"
                    )

                if downloaded_file and os.path.exists(downloaded_file):
                    file_size = os.path.getsize(downloaded_file)
                    file_size_mb = file_size / (1024 * 1024)
                    print(f"[DOWNLOAD] File ditemukan: {downloaded_file} | Ukuran: {file_size_mb:.2f} MB")
                    
                    if file_size > 50 * 1024 * 1024:
                        os.remove(downloaded_file)
                        await message.reply("❌ Video terlalu besar (>50MB).")
                        return

                    embed = discord.Embed(
                        description=description[:4096], color=discord.Color.blurple()
                    )
                    embed.set_author(name=f"@{uploader}")
                    embed.set_footer(
                        text=f"Requested by: {message.author}",
                        icon_url=message.author.display_avatar.url,
                    )

                    # Routing ke Uguu jika > 24MB
                    if file_size > 24 * 1024 * 1024:
                        print(f"[ROUTING] Ukuran {file_size_mb:.2f}MB > 24MB. Mengunggah ke Uguu...")
                        file_url = upload_to_cloud(downloaded_file)
                        
                        if file_url:
                            print(f"[ROUTING] Berhasil upload ke Uguu: {file_url}")
                            await message.reply(embed=embed)
                            await message.channel.send(file_url)
                        else:
                            print("[ROUTING] Gagal upload ke Uguu!")
                            await message.reply("❌ Gagal mengunggah video besar ke server cloud cadangan.")
                    else:
                        print(f"[ROUTING] Ukuran {file_size_mb:.2f}MB <= 24MB. Mengirim langsung ke Discord...")
                        file = discord.File(downloaded_file, filename="video.mp4")
                        await message.reply(embed=embed, file=file)

                    os.remove(downloaded_file)
                else:
                    await message.reply("Gagal mengunduh video dari tautan tersebut.")

            except Exception as e:
                error_msg = str(e)
                print(f"[ERROR] Terjadi kesalahan: {error_msg}")
                if "Video not available" in error_msg:
                    await message.reply("❌ Gagal mengunduh: TikTok memblokir IP server atau video dihapus/privat.")
                elif "Sign in" in error_msg or "bot" in error_msg:
                    await message.reply("❌ YouTube memblokir akses bot sementara.")
                elif "DRM protected" in error_msg:
                    await message.reply("❌ Gagal mengunduh: Video ini dilindungi hak cipta DRM.")
                else:
                    await message.reply(f"Terjadi kesalahan saat memproses video: `{error_msg[:100]}`")
                
                if downloaded_file and os.path.exists(downloaded_file):
                    os.remove(downloaded_file)

    await bot.process_commands(message)

bot.run(os.getenv("DISCORD_TOKEN"))
