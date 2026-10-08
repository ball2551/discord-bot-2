import discord
from discord.ext import commands
from datetime import datetime

# กำหนด ID ของเซิร์ฟเวอร์ที่อนุญาตให้ใช้งาน
TARGET_GUILD_ID = 1555496169029767218

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# voice_sessions: เก็บเวลาเข้าห้อง {user_id: datetime}
# total_time: เก็บเวลารวม {user_id: total_seconds}
voice_sessions = {}
total_time = {}

@bot.event
async def on_ready():
    print(f'บอทเชื่อมต่อสำเร็จในชื่อ: {bot.user}')
    print(f'ล็อกการใช้งานเฉพาะ Guild ID: {TARGET_GUILD_ID}')

@bot.event
async def on_voice_state_update(member, before, after):
    # ป้องกันบอท และตรวจสอบว่าเป็นเซิร์ฟเวอร์ที่อนุญาตหรือไม่
    if member.bot or member.guild.id != TARGET_GUILD_ID:
        return

    user_id = member.id

    # 1. ยูสเซอร์เข้าห้องเสียง
    if before.channel is None and after.channel is not None:
        voice_sessions[user_id] = datetime.now()
        print(f"[{member.guild.name}] {member.display_name} เข้าห้อง {after.channel.name}")

    # 2. ยูสเซอร์ออกจากห้องเสียง
    elif before.channel is not None and after.channel is None:
        if user_id in voice_sessions:
            join_time = voice_sessions.pop(user_id)
            duration = (datetime.now() - join_time).total_seconds()
            
            total_time[user_id] = total_time.get(user_id, 0) + duration
            
            minutes = int(duration // 60)
            seconds = int(duration % 60)
            print(f"[{member.guild.name}] {member.display_name} ออกจากห้อง ใช้เวลาไป {minutes} นาที {seconds} วินาที")

# เช็คเวลาออนไลน์ (จำกัดเฉพาะเซิร์ฟเวอร์ที่กำหนด)
@bot.command(name="online")
async def check_online(ctx, member: discord.Member = None):
    # ป้องกันไม่ให้รันคำสั่งนอกเซิร์ฟเวอร์ที่กำหนด หรือใน DM
    if ctx.guild is None or ctx.guild.id != TARGET_GUILD_ID:
        return

    member = member or ctx.author
    user_id = member.id

    accumulated_seconds = total_time.get(user_id, 0)
    
    current_session_seconds = 0
    if user_id in voice_sessions:
        current_session_seconds = (datetime.now() - voice_sessions[user_id]).total_seconds()

    total_seconds = int(accumulated_seconds + current_session_seconds)

    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60

    embed = discord.Embed(
        title=f"⏱️ เวลาออนไลน์ใน Voice ของ {member.display_name}",
        color=discord.Color.blue()
    )
    embed.add_field(name="เวลารวมทั้งหมด", value=f"{hours} ชั่วโมง {minutes} นาที {seconds} วินาที", inline=False)
    
    if user_id in voice_sessions:
        embed.set_footer(text="🟢 กำลังออนไลน์อยู่ในห้องเสียง ณ ขณะนี้")
    else:
        embed.set_footer(text="🔴 ไม่ได้อยู่ในห้องเสียง")

    await ctx.send(embed=embed)

bot.run("YOUR_BOT_TOKEN_HERE")
