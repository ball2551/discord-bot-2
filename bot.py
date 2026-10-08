import discord
from discord.ext import commands
from datetime import datetime, timedelta
import json
import os

# กำหนด ID ของเซิร์ฟเวอร์ที่อนุญาตให้ใช้งาน
TARGET_GUILD_ID = 1555496169029767218
DATA_FILE = "voice_data.json"

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# voice_sessions: เก็บเวลาเข้าห้องปัจจุบัน {user_id: datetime}
voice_sessions = {}

# ฟังก์ชั่นโหลดข้อมูลจากไฟล์ JSON
def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"เกิดข้อผิดพลาดในการโหลดไฟล์ JSON: {e}")
            return {}
    return {}

# ฟังก์ชั่นบันทึกข้อมูลลงไฟล์ JSON
def save_data(data):
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"เกิดข้อผิดพลาดในการบันทึกไฟล์ JSON: {e}")

# ฟังก์ชั่นล้างข้อมูลประวัติที่เก่าเกิน 30 วัน
def cleanup_old_records(user_id_str, data):
    if user_id_str not in data:
        return
    
    today = datetime.now().date()
    cutoff_date = today - timedelta(days=30)
    
    updated_records = {}
    for date_str, seconds in data[user_id_str].items():
        record_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        if record_date >= cutoff_date:
            updated_records[date_str] = seconds
            
    data[user_id_str] = updated_records

# ฟังก์ชั่นบันทึกเวลาที่ใช้งานเพิ่มลงในประวัติประจำวัน
def add_voice_time(user_id, seconds):
    data = load_data()
    user_str = str(user_id)
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    if user_str not in data:
        data[user_str] = {}
        
    data[user_str][today_str] = data[user_str].get(today_str, 0) + seconds
    
    # ลบข้อมูลที่เก่าเกิน 30 วันออก
    cleanup_old_records(user_str, data)
    
    save_data(data)

# ฟังก์ชั่นคำนวณเวลารวมย้อนหลัง 30 วันของผู้ใช้
def get_total_time_30days(user_id):
    data = load_data()
    user_str = str(user_id)
    
    if user_str not in data:
        return 0
        
    cleanup_old_records(user_str, data)
    save_data(data)
    
    return sum(data[user_str].values())

@bot.event
async def on_ready():
    print(f'บอทเชื่อมต่อสำเร็จในชื่อ: {bot.user}')
    print(f'ล็อกการใช้งานเฉพาะ Guild ID: {TARGET_GUILD_ID}')

@bot.event
async def on_voice_state_update(member, before, after):
    # ตรวจสอบว่าเป็นบอทหรืออยู่นอกเซิร์ฟเวอร์ที่กำหนดหรือไม่
    if member.bot or member.guild.id != TARGET_GUILD_ID:
        return

    user_id = member.id

    # 1. เข้าห้องเสียง
    if before.channel is None and after.channel is not None:
        voice_sessions[user_id] = datetime.now()
        print(f"[{member.guild.name}] {member.display_name} เข้าห้อง {after.channel.name}")

    # 2. ออกจากห้องเสียง
    elif before.channel is not None and after.channel is None:
        if user_id in voice_sessions:
            join_time = voice_sessions.pop(user_id)
            duration = (datetime.now() - join_time).total_seconds()
            
            # บันทึกเวลาลงประวัติย้อนหลัง 30 วัน
            add_voice_time(user_id, duration)
            
            minutes = int(duration // 60)
            seconds = int(duration % 60)
            print(f"[{member.guild.name}] {member.display_name} ออกจากห้อง บันทึกเวลาเพิ่ม {minutes} นาที {seconds} วินาที")

@bot.command(name="online")
async def check_online(ctx, member: discord.Member = None):
    if ctx.guild is None or ctx.guild.id != TARGET_GUILD_ID:
        return

    member = member or ctx.author
    user_id = member.id

    # ดึงเวลารวมสะสมย้อนหลัง 30 วันจากไฟล์
    accumulated_seconds = get_total_time_30days(user_id)
    
    # คำนวณเวลาที่กำลังออนอยู่ในห้อง ณ ปัจจุบัน (ถ้ามี)
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
    embed.add_field(
        name="เวลารวมสะสม (ย้อนหลัง 30 วัน)", 
        value=f"{hours} ชั่วโมง {minutes} นาที {seconds} วินาที", 
        inline=False
    )
    
    if user_id in voice_sessions:
        embed.set_footer(text="🟢 กำลังออนไลน์อยู่ในห้องเสียง ณ ขณะนี้")
    else:
        embed.set_footer(text="🔴 ไม่ได้อยู่ในห้องเสียง")

    await ctx.send(embed=embed)

# ดึง Token จาก Railway Variable (ชื่อ DISCORD_TOKEN)
bot.run(os.getenv("DISCORD_TOKEN"))
