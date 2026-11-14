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

# Fungsi untuk mengunggah file ke Litterbox dengan header browser & MIME type
def upload_to_catbox(file_path):
    url = "https://litterbox.moe/api.php"
    try:
        filename = os.path.basename(file_path)
        with open(file_path, "rb") as f:
            # Menggunakan tuple dengan menyertakan nama file dan MIME type video/mp4
            files = {"fileToUpload": (filename, f, "video/mp4")}
            data = {
                "reqtype": "fileupload",
                "time": "24h"  # File disimpan selama 24 jam
            }
            # Header browser wajib agar tidak diblokir oleh server Litterbox
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            response = requests.post(url, data=data, files=files, headers=headers, timeout=60)
            print(f"[LITTERBOX] Status: {response.status_code}")
            print(f"[LITTERBOX] Response: {response.text}")
            
            if response.status_code == 200 and "litterbox.moe" in response.text:
                return response.text.strip()
    except Exception as e:
        print(f"[LITTERBOX] Gagal upload: {e}")
    return None

@bot.event
async def on_ready():
    print("=== BOT CATBOX 7MB AKTIF ===")
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

                    if file_size > 7 * 1024 * 1024:
                        print(f"[ROUTING] Ukuran {file_size_mb:.2f}MB > 7MB. Mengunggah ke Litterbox...")
                        file_url = upload_to_catbox(downloaded_file)
                        
                        if file_url:
                            print(f"[ROUTING] Berhasil upload ke Litterbox: {file_url}")
                            embed.add_field(
                                name="📦 Video Berukuran Besar (>7MB)",
                                value=f"[Klik di sini untuk menonton / mengunduh video]({file_url})",
                                inline=False
                            )
                            await message.reply(embed=embed)
                        else:
                            print("[ROUTING] Gagal upload ke Litterbox!")
                            await message.reply("❌ Gagal mengunggah video besar ke server cloud cadangan.")
                    else:
                        print(f"[ROUTING] Ukuran {file_size_mb:.2f}MB <= 7MB. Mengirim langsung ke Discord...")
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
