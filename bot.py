import os
import re
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

# Fungsi upload menggunakan Uguu.se (100% aman dan tembus di server cloud Railway)
def upload_to_cloud(file_path):
    url = "https://uguu.se/upload?output=text"
    try:
        with open(file_path, "rb") as f:
            files = {"files[]": f}
            response = requests.post(url, files=files, timeout=60)
            print(f"[UGUU] Status: {response.status_code}")
            print(f"[UGUU] Response: {response.text}")
            
            if response.status_code == 200 and "uguu.se" in response.text:
                return response.text.strip()
    except Exception as e:
        print(f"[UGUU] Gagal upload: {e}")
    return None

@bot.event
async def on_ready():
    print("=== BOT MULTI-PLATFORM AKTIF ===")
    print(f"Bot masuk sebagai {bot.user} (ID: {bot.user.id})")

@bot.event
async def on_message(message):
    if message.author.bot:
        await bot.process_commands(message)
        return

    match = MULTI_PLATFORM_REGEX.search(message.content)
    if match:
        url = match.group(0)
        downloaded_file = None

        async with message.channel.typing():
            try:
                ydl_opts = {
                    "outtmpl": f"media_{message.id}.%(ext)s",
                    "noplaylist": True,
                    "quiet": True,
                    "format": "best[ext=mp4]/best",
                    "extractor_args": {
                        "youtube": {
                            "player_client": ["android", "web"]
                        }
                    },
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

                    # Jika file > 24MB, upload ke Uguu.se (Mencegah error 413 Discord)
                    if file_size > 24 * 1024 * 1024:
                        print(f"[ROUTING] Ukuran {file_size_mb:.2f}MB > 24MB. Mengunggah ke Uguu.se...")
                        file_url = upload_to_cloud(downloaded_file)
                        
                        if file_url:
                            print(f"[ROUTING] Berhasil upload ke Uguu: {file_url}")
                            embed.add_field(
                                name="📦 Video Berukuran Besar (>24MB)",
                                value=f"[Klik di sini untuk menonton / mengunduh video]({file_url})",
                                inline=False
                            )
                            await message.reply(embed=embed)
                        else:
                            print("[ROUTING] Gagal upload ke Uguu!")
                            await message.reply("❌ Gagal mengunggah video besar ke server cloud cadangan.")
                    
                    # Jika <= 24MB, kirim langsung ke Discord dengan aman
                    else:
                        print(f"[ROUTING] Ukuran {file_size_mb:.2f}MB <= 24MB. Mengirim langsung ke Discord...")
                        file = discord.File(downloaded_file, filename="video.mp4")
                        await message.reply(embed=embed, file=file)

                    os.remove(downloaded_file)
                else:
                    await message.reply("Gagal mengunduh video dari tautan tersebut.")

            except Exception as e:
                print(f"[ERROR] Terjadi kesalahan: {e}")
                await message.reply(f"Terjadi kesalahan saat memproses video: `{e}`")
                if downloaded_file and os.path.exists(downloaded_file):
                    os.remove(downloaded_file)

    await bot.process_commands(message)

bot.run(os.getenv("DISCORD_TOKEN"))