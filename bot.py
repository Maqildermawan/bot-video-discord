import os
import re
import discord
from discord.ext import commands
import yt_dlp
import requests

# Mengatur intents agar bot bisa membaca isi pesan
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Regex gabungan untuk mendeteksi TikTok, Instagram, YouTube, dan Twitter/X
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

# Fungsi untuk mengunggah file besar ke Catbox.moe dengan Header User-Agent
def upload_to_catbox(file_path):
    url = "https://catbox.moe/user/api.php"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        with open(file_path, "rb") as f:
            files = {"fileToUpload": f}
            data = {"reqtype": "upload-file"}
            response = requests.post(url, data=data, files=files, headers=headers, timeout=60)
            print(f"Catbox Response Status: {response.status_code}")
            print(f"Catbox Response Text: {response.text}")
            
            if response.status_code == 200:
                return response.text.strip()
    except Exception as e:
        print(f"Gagal upload ke cloud: {e}")
    return None

@bot.event
async def on_ready():
    print(f"Bot masuk sebagai {bot.user} (ID: {bot.user.id})")
    print("Siap mendeteksi video dari TikTok, IG, Shorts, & Twitter/X!")

@bot.event
async def on_message(message):
    if message.author.bot:
        await bot.process_commands(message)
        return

    match = MULTI_PLATFORM_REGEX.search(message.content)
    if match:
        url = match.group(0)
        downloaded_file = None

        # Tampilkan status typing saat bot mendownload video
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

                # Mengunduh video menggunakan yt-dlp
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    downloaded_file = ydl.prepare_filename(info)

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
                    
                    # Batasi maksimal 50MB sesuai permintaan
                    if file_size > 50 * 1024 * 1024:
                        os.remove(downloaded_file)
                        await message.reply("❌ Video terlalu besar (>50MB).")
                        return

                    # Membuat tampilan Embed yang rapi
                    embed = discord.Embed(
                        description=description[:4096], color=discord.Color.blurple()
                    )
                    embed.set_author(name=f"@{uploader}")
                    embed.set_footer(
                        text=f"Requested by: {message.author}",
                        icon_url=message.author.display_avatar.url,
                    )

                    # SKENARIO 1: Jika file <= 25MB, kirim langsung sebagai file Discord
                    if file_size <= 24 * 1024 * 1024:
                        file = discord.File(downloaded_file, filename="video.mp4")
                        await message.reply(embed=embed, file=file)

                    # SKENARIO 2: Jika file di atas 25MB hingga 50MB, upload ke Cloud agar lolos dari limit Discord
                    else:
                        file_url = upload_to_catbox(downloaded_file)
                        if file_url:
                            embed.add_field(
                                name="📦 Video Berukuran Besar (>25MB)",
                                value=f"[Klik di sini untuk menonton / mengunduh video]({file_url})",
                                inline=False
                            )
                            await message.reply(embed=embed)
                        else:
                            await message.reply("❌ Gagal mengunggah video besar ke server cloud cadangan.")

                    # Hapus file dari penyimpanan lokal Railway setelah selesai
                    os.remove(downloaded_file)
                else:
                    await message.reply("Gagal mengunduh video dari tautan tersebut.")

            except Exception as e:
                print(f"Error saat memproses video: {e}")
                await message.reply(f"Terjadi kesalahan saat memproses video: `{e}`")
                if downloaded_file and os.path.exists(downloaded_file):
                    os.remove(downloaded_file)

    await bot.process_commands(message)

bot.run(os.getenv("DISCORD_TOKEN"))
