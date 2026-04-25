import discord 
from discord.ext import commands
import requests
import math 
import os 
import re
import time
import yt_dlp
import asyncio
from datetime import datetime

# --- ⚙️ ボットの基本設定 ---
intents = discord.Intents.default()
intents.message_content = True 
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

log_settings = {}
intro_settings = {}

@bot.event
async def on_ready():
    print(f"✅ ログイン完了: {bot.user}")

# --- 🎶 音楽再生・操作系 ---
@bot.command()
async def misu(ctx, url: str):
    if not ctx.author.voice:
        return await ctx.send("❌ まずはボイスチャンネルに入ってね！")
    channel = ctx.author.voice.channel
    if ctx.voice_client is None: await channel.connect(reconnect=True, timeout=20)
    elif ctx.voice_client.channel != channel: await ctx.voice_client.move_to(channel)
    async with ctx.typing():
        try:
            ydl_opts = {'format': 'bestaudio/best', 'noplaylist': True, 'quiet': True}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                url2 = info['url']
                title = info.get('title', '不明な曲')
                if ctx.voice_client.is_playing(): ctx.voice_client.stop()
                source = await discord.FFmpegOpusAudio.from_probe(url2, 
                    before_options='-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
                    options='-vn')
                ctx.voice_client.play(source)
                await ctx.send(f"🎶 **再生中:** {title}")
        except Exception as e: await ctx.send(f"⚠️ エラー: {e}")

@bot.command()
async def skip(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("⏭️ 曲をスキップしたよ！")

@bot.command()
async def stop(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("👋 バイバイ！")

# --- 📡 航空情報系 ---
@bot.command()
async def metar(ctx, code: str):
    res = requests.get(f"https://tgftp.nws.noaa.gov/data/observations/metar/stations/{code.upper()}.TXT")
    if res.status_code == 200: await ctx.send(f"✈️ **{code.upper()} METAR:**\n```{res.text}```")
    else: await ctx.send("❌ 取得失敗")

@bot.command()
async def plan(ctx):
    res = requests.get(f"https://www.simbrief.com/api/xml.fetcher.php?userid=906331&json=1")
    if res.status_code == 200:
        data = res.json()
        tk = data.get('takeoff', {})
        await ctx.send(f"📋 **SimBrief Plan**\nV1: `{tk.get('v1','--')}` / VR: `{tk.get('vr','--')}` / V2: `{tk.get('v2','--')}`\nRoute: `{data['general']['route']}`")

@bot.command()
async def vatsim(ctx, icao: str):
    res = requests.get("https://data.vatsim.net/v3/vatsim-data.json")
    if res.status_code == 200:
        pilots = [p for p in res.json().get("pilots", []) if (p.get("flight_plan") or {}).get("departure") == icao.upper() or (p.get("flight_plan") or {}).get("arrival") == icao.upper()]
        msg = f"📡 **VATSIM {icao.upper()}**\n" + ("\n".join([f"• `{p['callsign']}` {p['altitude']}ft" for p in pilots[:5]]) if pilots else "なし")
        await ctx.send(msg)

@bot.command()
async def flights(ctx, icao: str):
    icao = icao.upper(); now = int(time.time())
    try:
        arr = requests.get(f"https://opensky-network.org/api/flights/arrival?airport={icao}&begin={now-3600}&end={now+3600}").json()
        dep = requests.get(f"https://opensky-network.org/api/flights/departure?airport={icao}&begin={now-3600}&end={now+3600}").json()
        embed = discord.Embed(title=f"✈️ {icao} Board", color=0x1d2731)
        embed.add_field(name="Arrivals", value="\n".join([f"🛬 `{f['callsign'].strip()}`" for f in arr[:5]]) if arr else "なし", inline=True)
        embed.add_field(name="Departures", value="\n".join([f"🛫 `{f['callsign'].strip()}`" for f in dep[:5]]) if dep else "なし", inline=True)
        await ctx.send(embed=embed)
    except: await ctx.send("❌ エラー")

# --- 📐 計算・変換系 ---
@bot.command()
async def td(ctx, cur: int, tar: int, gs: int):
    dist = ((cur - tar) / 1000) * 3
    rate = gs * 5
    await ctx.send(f"📉 **降下計算:** `{dist:.1f} NM` 手前から `-{rate} fpm` で降下開始！")

@bot.command()
async def xwind(ctx, rwy: str, w_dir: int, w_spd: int):
    try:
        r_dir = int(re.search(r'\d+', rwy).group()) * 10
        xw = abs(w_spd * math.sin(math.radians(abs(r_dir - w_dir))))
        await ctx.send(f"🌬️ **RWY{rwy} 横風:** `{xw:.1f} KT` だよ。")
    except: await ctx.send("❌ エラー")

@bot.command()
async def unit(ctx, val: float, mode: str):
    if mode == "lbkg": await ctx.send(f"⚖️ `{val} LB` ➔ `{val / 2.20462:.1f} KG`")
    elif mode == "kglb": await ctx.send(f"⚖️ `{val} KG` ➔ `{val * 2.20462:.1f} LB`")

# --- 🛠️ 管理・自己紹介系 ---
async def send_intro_template(channel):
    msg = ("**📝 自己紹介テンプレ **\n━━━━━━━━━━━━━━\n"
           "⚠️ **読んで欲しい名前：**\n🔹 **年齢：**\n🔹 **性別：**\n"
           "⚠️ **やってるゲーム：**\n🔹 **趣味・好きなもの：**\n⚠️ **一言：**\n"
           "━━━━━━━━━━━━━━\n※⚠️は必須入力項目だよ！")
    await channel.send(msg)

@bot.command()
async def intro(ctx): await send_intro_template(ctx.channel)

@bot.command()
@commands.has_permissions(administrator=True)
async def setintro(ctx):
    intro_settings[ctx.guild.id] = ctx.channel.id
    await ctx.send(f"✅ {ctx.channel.mention} を自己紹介チャンネルに設定！")

@bot.command()
@commands.has_permissions(administrator=True)
async def removeintro(ctx):
    if ctx.guild.id in intro_settings:
        del intro_settings[ctx.guild.id]
        await ctx.send("📴 自己紹介機能を解除したよ。")

@bot.command()
@commands.has_permissions(administrator=True)
async def setlog(ctx):
    log_settings[ctx.guild.id] = ctx.channel.id
    await ctx.send(f"✅ {ctx.channel.mention} を削除ログに設定！")

@bot.command()
@commands.has_permissions(administrator=True)
async def removelog(ctx):
    if ctx.guild.id in log_settings:
        del log_settings[ctx.guild.id]
        await ctx.send("📴 削除ログを解除したよ。")

# --- 📩 イベント ---
@bot.event
async def on_message(message):
    if message.author.bot: return
    if message.guild and message.guild.id in intro_settings:
        if message.channel.id == intro_settings[message.guild.id] and not message.content.startswith('!'):
            async for old in message.channel.history(limit=10):
                if old.author == bot.user and "**📝 自己紹介テンプレ **" in old.content:
                    try: await old.delete()
                    except: pass
            await send_intro_template(message.channel)
    await bot.process_commands(message)

@bot.event
async def on_message_delete(message):
    if message.author.bot or not message.guild: return
    log_id = log_settings.get(message.guild.id)
    if not log_id: return
    log_ch = message.guild.get_channel(log_id)
    if not log_ch: return
    embed = discord.Embed(title="🗑️ メッセージ削除", color=0xff0000, timestamp=datetime.now())
    embed.set_thumbnail(url="https://emojicdn.elk.sh/🤔")
    embed.add_field(name="👤 ユーザー", value=f"{message.author.mention}\n({message.author.name})", inline=True)
    embed.add_field(name="📍 チャンネル", value=message.channel.mention, inline=True)
    embed.add_field(name="⏰ 投稿時刻", value=message.created_at.strftime("%Y/%m/%d %H:%M:%S"), inline=True)
    embed.add_field(name="📝 内容", value=f"```\n{message.content if message.content else 'なし'}\n```", inline=False)
    embed.set_footer(text=f"User ID: {message.author.id}")
    await log_ch.send(embed=embed)

# --- 📚 ヘルプ ---
@bot.command()
async def help(ctx):
    e = discord.Embed(color=0x00ff00)
    e.add_field(name="🎶 音楽", value=(
        "!misu [URL]：YouTubeを再生\n"
        "!skip：今の曲を飛ばす\n"
        "!stop：音楽を止めて退出"
    ), inline=False)
    e.add_field(name="📡 航空", value=(
        "!metar [ICAO]：気象情報の取得\n"
        "!plan：SimBriefフライトプラン取得\n"
        "!flights [ICAO]：空港の発着便を表示\n"
        "!vatsim [ICAO]：VATSIM上のトラフィックを表示"
    ), inline=False)
    e.add_field(name="📐 計算", value=(
        "!td [高度] [目標] [速度]：降下開始地点の計算\n"
        "!xwind [RWY] [風向] [風速]：横風成分の計算\n"
        "!unit [値] [lbkg/kglb]：重さの単位変換"
    ), inline=False)
    e.add_field(name="🛠️ 管理", value=(
        "!intro：自己紹介テンプレを手動表示\n"
        "!setintro / !removeintro：自己紹介自動化の設定/解除\n"
        "!setlog / !removelog：削除ログの設定/解除\n"
        "!reboot：ボットの再起動（終了）"
    ), inline=False)
    e.set_footer(text="みっくん専用 EFB Pro")
    await ctx.send(embed=e)

@bot.command()
async def reboot(ctx):
    await ctx.send("🔄 終了。"); await bot.close()

if __name__ == "__main__":
    # Renderなどの環境変数からトークンを読み込む
    token = os.getenv("DISCORD_BOT_TOKEN")
    if token:
        bot.run(token)
    else:
        print("❌ トークンが見つかりません。環境変数 'DISCORD_BOT_TOKEN' を設定してください。")