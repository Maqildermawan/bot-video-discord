import os
import re
import discord
from discord.ext import commands
import yt_dlp

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
            # Meminjam cookies dari browser Chrome (pastikan kamu sudah login IG di Chrome)
            # Jika pakai Edge, ganti 'chrome' menjadi 'edge'
            "cookiefrombrowser": ("chrome",),
        }

        # Mengunduh video menggunakan yt-dlp
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
          info = yt_dlp.YoutubeDL(ydl_opts).extract_info(url, download=True)
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

        # Cek apakah file berhasil diunduh dan ada di direktori
        if downloaded_file and os.path.exists(downloaded_file):
          file_size = os.path.getsize(downloaded_file)
          if file_size > 50 * 1024 * 1024:
            os.remove(downloaded_file)
            await message.reply(
                "❌ Video terlalu besar untuk diunggah ke Discord (>50MB)."
            )
            return

          file = discord.File(downloaded_file, filename="video.mp4")

          # Membuat tampilan Embed yang rapi
          embed = discord.Embed(
              description=description[:4096], color=discord.Color.blurple()
          )

          # Menampilkan nama uploader di bagian atas embed
          embed.set_author(name=f"@{uploader}")

          # Menampilkan footer "Requested by" beserta foto profil pembuat pesan
          embed.set_footer(
              text=f"Requested by: {message.author}",
              icon_url=message.author.display_avatar.url,
          )

          # Kirim pesan dengan embed dan file video
          await message.reply(embed=embed, file=file)

          # Hapus file dari penyimpanan lokal setelah terkirim
          os.remove(downloaded_file)
        else:
          await message.reply("Gagal mengunduh video dari tautan tersebut.")

      except Exception as e:
        print(f"Error saat memproses video: {e}")
        await message.reply(
            f"Terjadi kesalahan saat memproses video: `{e}`"
        )
        if downloaded_file and os.path.exists(downloaded_file):
          os.remove(downloaded_file)

  await bot.process_commands(message)

bot.run(os.getenv("DISCORD_TOKEN"))
