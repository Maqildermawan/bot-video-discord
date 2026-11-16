import os
import re
import asyncio
import discord
import yt_dlp
import requests

TOKEN = os.getenv("DISCORD_TOKEN")
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID", 0))

intents = discord.Intents.default()
intents.message_content = True
bot = discord.Client(intents=intents)

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

@bot.event
async def on_ready():
    print(f"=== BOT MULTI-PLATFORM STABLE V4 ===")
    print(f"Bot masuk sebagai {bot.user} (ID: {bot.user.id})")

async def send_log(guild, user, action, details, file_path=None, file_name="video.mp4", cloud_url=None):
    if LOG_CHANNEL_ID == 0:
        return
    
    channel = bot.get_channel(LOG_CHANNEL_ID)
    if channel:
        embed = discord.Embed(
            title="📊 Bot Activity Log",
            color=discord.Color.green() if file_path or cloud_url else discord.Color.red(),
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(name="Pengguna", value=f"{user} (`{user.id}`)", inline=False)
        embed.add_field(name="Server", value=f"{guild.name if guild else 'Direct Message'}", inline=False)
        embed.add_field(name="Aktivitas", value=action, inline=False)
        embed.add_field(name="Detail", value=details, inline=False)
        
        if cloud_url:
            embed.add_field(name="Link Video (Cloud)", value=cloud_url, inline=False)

        if file_path and os.path.exists(file_path):
            file_size = os.path.getsize(file_path)
            if file_size <= 24 * 1024 * 1024:
                await channel.send(embed=embed, file=discord.File(file_path, filename=file_name))
                return

        await channel.send(embed=embed)

def download_media(url, unique_id):
    output_template = os.path.join(DOWNLOAD_DIR, f"{unique_id}.%(ext)s")
    
    ydl_opts = {
        'format': 'b[filesize<24M]/b/bv*+ba/b',
        'outtmpl': output_template,
        'noplaylist': True,
        'quiet': True,
        'cookiefile': 'cookies.txt' if os.path.exists('cookies.txt') else None,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        if not os.path.exists(filename):
            base = os.path.splitext(filename)[0]
            for ext in ['mp4', 'mkv', 'webm', 'mov']:
                if os.path.exists(f"{base}.{ext}"):
                    filename = f"{base}.{ext}"
                    break
        return info, filename

def upload_to_uguu(file_path):
    with open(file_path, 'rb') as f:
        response = requests.post('https://uguu.se/upload', files={'files[]': f}, timeout=60)
    data = response.json()
    if data.get('success'):
        return data['files'][0]['url']
    raise Exception("Gagal mengunggah file besar ke server cloud.")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    url_match = re.search(r'(https?://[^\s]+)', message.content)
    if not url_match:
        return

    url = url_match.group(0)
    status_msg = await message.reply("⏳ Sedang mengunduh video, mohon tunggu...")

    file_path = None
    try:
        loop = asyncio.get_running_loop()
        info, file_path = await loop.run_in_executor(None, download_media, url, message.id)

        title = info.get('title', 'Video')
        safe_title = re.sub(r'[\\/*?:"<>|]', "", title)[:50] + ".mp4"
        uploader = info.get('uploader') or info.get('channel') or 'Creator'
        description = info.get('description') or ''
        
        if len(description) > 350:
            description = description[:347] + "..."

        embed = discord.Embed(
            description=f"**@{uploader}**\n{description}" if description else f"**@{uploader}**",
            color=discord.Color.from_rgb(43, 45, 49)
        )

        file_size = os.path.getsize(file_path)
        max_discord_size = 24 * 1024 * 1024  # 24 MB

        if file_size <= max_discord_size:
            await status_msg.delete()
            await message.reply(
                file=discord.File(file_path, filename=safe_title),
                embed=embed
            )
            await send_log(
                message.guild, message.author, "Download Video",
                f"Judul: {title}\nURL: {url}",
                file_path=file_path, file_name=safe_title
            )
        else:
            await status_msg.edit(content="📦 Ukuran video melebihi batas Discord, mengunggah ke cloud...")
            cloud_url = await loop.run_in_executor(None, upload_to_uguu, file_path)
            await status_msg.delete()
            await message.reply(content=f"{cloud_url}", embed=embed)
            await send_log(
                message.guild, message.author, "Download Video (Cloud)",
                f"Judul: {title}\nURL: {url}",
                cloud_url=cloud_url
            )

        try:
            await message.edit(suppress=True)
        except Exception:
            pass

    except Exception as e:
        await status_msg.edit(content="❌ Gagal mengunduh video. Pastikan link publik atau format didukung.")
        print(f"[ERROR] {e}")
        await send_log(message.guild, message.author, "Error Download", f"URL: {url}\nError: `{e}`")

    finally:
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass

if __name__ == "__main__":
    bot.run(TOKEN)