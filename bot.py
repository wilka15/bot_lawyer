import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button
import re
import os
import json
import hashlib
import asyncio
from datetime import datetime, timedelta
from difflib import get_close_matches
from threading import Thread
from flask import Flask, request, jsonify
import google.generativeai as genai

# ===== ВЕБ-СЕРВЕР =====
app = Flask(__name__)

@app.route('/')
def health_check():
    return "✅ Bot is alive!", 200

@app.route('/api/stats')
def api_stats():
    data = load_data()
    stats = get_premium_stats()
    
    total_requests = 0
    current_month = datetime.now().strftime("%Y-%m")
    for user_id, info in data.items():
        if info.get("month") == current_month:
            total_requests += info.get("requests", 0)
    
    return jsonify({
        "total_users": stats['total_users'],
        "active_premium": stats['active_premium'],
        "total_requests": total_requests,
        "month": stats['month'],
        "uk_articles": len(uk_laws),
        "pk_articles": len(pk_laws),
        "status": "online",
        "uptime": "24/7"
    })

def run_web_server():
    app.run(host='0.0.0.0', port=8080)

# ===== НАСТРОЙКИ =====
TOKEN = os.environ.get("DISCORD_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

if not TOKEN:
    print("❌ ОШИБКА: DISCORD_TOKEN не найден!")
    exit(1)
if not GEMINI_API_KEY:
    print("❌ ОШИБКА: GEMINI_API_KEY не найден!")
    exit(1)

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash')

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# ===== ID ВЛАДЕЛЬЦА БОТА =====
OWNER_ID = 920268444983775252  # ⚠️ ЗАМЕНИТЕ НА ВАШ DISCORD ID!

def is_owner(interaction: discord.Interaction) -> bool:
    return interaction.user.id == OWNER_ID

# ========== СИСТЕМА ПОДПИСКИ ==========
DATA_FILE = "premium_users.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def cleanup_expired():
    data = load_data()
    changed = False
    now = datetime.now()
    
    for user_id, info in list(data.items()):
        premium_until = info.get("premium_until")
        if premium_until:
            expire_date = datetime.fromisoformat(premium_until)
            if expire_date <= now:
                data[user_id]["premium_until"] = None
                changed = True
                print(f"⏰ Подписка пользователя {user_id} истекла")
    
    if changed:
        save_data(data)

def get_user_requests(user_id: str) -> int:
    data = load_data()
    current_month = datetime.now().strftime("%Y-%m")
    
    if user_id not in data:
        data[user_id] = {"requests": 0, "month": current_month, "premium_until": None, "bonus_requests": 0}
    
    if data[user_id].get("month") != current_month:
        data[user_id]["requests"] = 0
        data[user_id]["month"] = current_month
    
    save_data(data)
    return data[user_id]["requests"]

def increment_requests(user_id: str) -> int:
    data = load_data()
    current_month = datetime.now().strftime("%Y-%m")
    
    if user_id not in data:
        data[user_id] = {"requests": 0, "month": current_month, "premium_until": None, "bonus_requests": 0}
    
    if data[user_id].get("month") != current_month:
        data[user_id]["requests"] = 0
        data[user_id]["month"] = current_month
    
    data[user_id]["requests"] += 1
    save_data(data)
    return data[user_id]["requests"]

def is_premium(user_id: str) -> bool:
    cleanup_expired()
    data = load_data()
    if user_id not in data:
        return False
    
    premium_until = data[user_id].get("premium_until")
    if not premium_until:
        return False
    
    expire_date = datetime.fromisoformat(premium_until)
    return expire_date > datetime.now()

def add_premium(user_id: str, days: int):
    data = load_data()
    current_month = datetime.now().strftime("%Y-%m")
    
    if user_id not in data:
        data[user_id] = {"requests": 0, "month": current_month, "premium_until": None, "bonus_requests": 0}
    
    current_expiry = data[user_id].get("premium_until")
    if current_expiry:
        new_expiry = datetime.fromisoformat(current_expiry) + timedelta(days=days)
    else:
        new_expiry = datetime.now() + timedelta(days=days)
    
    data[user_id]["premium_until"] = new_expiry.isoformat()
    save_data(data)
    print(f"💎 Премиум выдан {user_id} на {days} дней до {new_expiry.strftime('%Y-%m-%d')}")
    return new_expiry

def get_premium_expiry(user_id: str) -> str:
    data = load_data()
    if user_id not in data:
        return None
    return data[user_id].get("premium_until")

def get_bonus_requests(user_id: str) -> int:
    data = load_data()
    if user_id not in data:
        return 0
    return data[user_id].get("bonus_requests", 0)

def add_bonus_requests(user_id: str, amount: int):
    data = load_data()
    current_month = datetime.now().strftime("%Y-%m")
    
    if user_id not in data:
        data[user_id] = {"requests": 0, "month": current_month, "premium_until": None, "bonus_requests": 0}
    
    data[user_id]["bonus_requests"] = data[user_id].get("bonus_requests", 0) + amount
    save_data(data)

def get_remaining_free_requests(user_id: str) -> int:
    used = get_user_requests(user_id)
    bonus = get_bonus_requests(user_id)
    return max(0, (5 + bonus) - used)

def get_all_premium_users() -> list:
    cleanup_expired()
    data = load_data()
    premium_list = []
    now = datetime.now()
    
    for user_id, info in data.items():
        premium_until = info.get("premium_until")
        if premium_until:
            expire_date = datetime.fromisoformat(premium_until)
            if expire_date > now:
                premium_list.append({
                    "id": user_id,
                    "expires": premium_until,
                    "expires_date": expire_date
                })
    
    premium_list.sort(key=lambda x: x["expires_date"])
    return premium_list

def get_premium_stats() -> dict:
    data = load_data()
    total_users = len(data)
    active_premium = 0
    now = datetime.now()
    
    for user_id, info in data.items():
        premium_until = info.get("premium_until")
        if premium_until:
            expire_date = datetime.fromisoformat(premium_until)
            if expire_date > now:
                active_premium += 1
    
    return {
        "total_users": total_users,
        "active_premium": active_premium,
        "month": datetime.now().strftime("%Y-%m")
    }

# ========== РЕФЕРАЛЬНАЯ СИСТЕМА ==========
REF_FILE = "referrals.json"

def load_ref_data():
    if os.path.exists(REF_FILE):
        with open(REF_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"codes": {}, "used": {}}

def save_ref_data(data):
    with open(REF_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def generate_ref_code(user_id: str) -> str:
    return hashlib.md5(f"{user_id}{OWNER_ID}".encode()).hexdigest()[:8].upper()

def get_user_ref_code(user_id: str) -> str:
    data = load_ref_data()
    if user_id not in data["codes"]:
        data["codes"][user_id] = generate_ref_code(user_id)
        save_ref_data(data)
    return data["codes"][user_id]

def get_user_by_ref_code(code: str) -> str:
    data = load_ref_data()
    for user_id, user_code in data["codes"].items():
        if user_code == code.upper():
            return user_id
    return None

def add_referral(referred_id: str, referrer_id: str) -> bool:
    data = load_ref_data()
    if referred_id in data["used"]:
        return False
    
    data["used"][referred_id] = {
        "referrer": referrer_id,
        "date": datetime.now().isoformat()
    }
    save_ref_data(data)
    
    add_bonus_requests(referred_id, 5)
    add_premium(referrer_id, 14)
    return True

def get_referral_stats(user_id: str) -> dict:
    data = load_ref_data()
    invited = []
    for referred_id, info in data["used"].items():
        if info["referrer"] == user_id:
            invited.append(referred_id)
    return {"count": len(invited), "invited": invited}

# ========== КНОПКИ ДЛЯ ПОДТВЕРЖДЕНИЯ ОПЛАТЫ ==========
class PaymentConfirmView(View):
    def __init__(self, user_id: str, days: int, price: int):
        super().__init__(timeout=3600)
        self.user_id = user_id
        self.days = days
        self.price = price
    
    @discord.ui.button(label="✅ Подтвердить оплату", style=discord.ButtonStyle.green, emoji="✅")
    async def confirm(self, interaction: discord.Interaction, button: Button):
        if not is_owner(interaction):
            await interaction.response.send_message("❌ Только для владельца бота!", ephemeral=True)
            return
        
        add_premium(self.user_id, self.days)
        
        embed = discord.Embed(
            title="✅ Премиум активирован!",
            description=f"Премиум на **{self.days}** дней активирован!",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)
        
        user = await bot.fetch_user(int(self.user_id))
        if user:
            await user.send(f"✅ Ваш премиум на **{self.days}** дней активирован! Спасибо за поддержку!")
        
        self.stop()
    
    @discord.ui.button(label="❌ Отклонить", style=discord.ButtonStyle.red, emoji="❌")
    async def reject(self, interaction: discord.Interaction, button: Button):
        if not is_owner(interaction):
            await interaction.response.send_message("❌ Только для владельца бота!", ephemeral=True)
            return
        
        await interaction.response.send_message(f"❌ Заявка отклонена", ephemeral=False)
        
        user = await bot.fetch_user(int(self.user_id))
        if user:
            await user.send(f"❌ Ваша заявка на премиум отклонена. Проверьте правильность оплаты или обратитесь в поддержку.")
        
        self.stop()

# ========== КНОПКИ ВЫБОРА СРОКА ПОДПИСКИ ==========
class PremiumDurationView(View):
    def __init__(self, user_id: str):
        super().__init__(timeout=120)
        self.user_id = user_id
    
    @discord.ui.button(label="30 дней - 55 ₽", style=discord.ButtonStyle.green, emoji="💎", row=0)
    async def premium_30(self, interaction: discord.Interaction, button: Button):
        await self.process_payment(interaction, 30, 55)
    
    @discord.ui.button(label="60 дней - 110 ₽", style=discord.ButtonStyle.blurple, emoji="💎", row=0)
    async def premium_60(self, interaction: discord.Interaction, button: Button):
        await self.process_payment(interaction, 60, 110)
    
    @discord.ui.button(label="90 дней - 165 ₽", style=discord.ButtonStyle.blurple, emoji="💎", row=1)
    async def premium_90(self, interaction: discord.Interaction, button: Button):
        await self.process_payment(interaction, 90, 165)
    
    @discord.ui.button(label="180 дней - 330 ₽", style=discord.ButtonStyle.blurple, emoji="💎", row=1)
    async def premium_180(self, interaction: discord.Interaction, button: Button):
        await self.process_payment(interaction, 180, 330)
    
    @discord.ui.button(label="365 дней - 660 ₽", style=discord.ButtonStyle.blurple, emoji="👑", row=2)
    async def premium_365(self, interaction: discord.Interaction, button: Button):
        await self.process_payment(interaction, 365, 660)
    
    async def process_payment(self, interaction: discord.Interaction, days: int, price: int):
        user_id = str(interaction.user.id)
        
        embed = discord.Embed(
            title=f"💎 Оплата подписки на {days} дней",
            description=(
                f"Сумма: **{price} ₽**\n\n"
                f"**Как оплатить:**\n"
                f"1. Переведите **{price} ₽** на карту: **[ 2200 2492 0252 2980 ]**\n"
                f"2. Напишите боту в **личные сообщения** и отправьте скриншот оплаты\n"
                f"3. Дождитесь подтверждения\n\n"
                f"**Ваш Discord ID:** `{user_id}`"
            ),
            color=discord.Color.gold()
        )
        await interaction.response.edit_message(content=None, embed=embed, view=None)

# ========== ОБРАБОТКА ЛИЧНЫХ СООБЩЕНИЙ ==========
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    
    if isinstance(message.channel, discord.DMChannel):
        if message.attachments:
            user_id = str(message.author.id)
            days = 30
            price = 55
            
            embed = discord.Embed(
                title="🆕 Новая заявка на премиум!",
                description=(
                    f"**Пользователь:** {message.author.mention}\n"
                    f"**Discord ID:** `{user_id}`\n"
                    f"**Срок:** {days} дней\n"
                    f"**Сумма:** {price} ₽"
                ),
                color=discord.Color.orange(),
                timestamp=datetime.now()
            )
            
            view = PaymentConfirmView(user_id, days, price)
            
            owner = await bot.fetch_user(OWNER_ID)
            if owner:
                await owner.send(embed=embed, view=view)
                for attachment in message.attachments:
                    await owner.send(f"📸 Скриншот: {attachment.url}")
            
            await message.reply(
                "✅ **Скриншот отправлен!**\n"
                "Владелец бота проверит оплату и активирует премиум.\n"
                "Статус: `/premium_status`"
            )
            return
    
    await bot.process_commands(message)

# ========== БАЗА УК ==========
uk_sections = {
    "VI": "Преступления против жизни и здоровья",
    "VII": "Преступления против свободы, чести и достоинства",
    "VIII": "Преступления против половой неприкосновенности",
    "X": "Преступления против собственности",
    "XI": "Преступления в сфере экономической деятельности",
    "XII": "Преступления против общественной безопасности",
    "XIII": "Преступления в сфере оборота наркотиков",
    "XV": "Преступления против власти",
    "XVI": "Преступления против правосудия",
    "XVII": "Преступления против управления",
    "XIX": "Преступления против окружающей среды",
}

uk_laws = [
    {"article": "6.1", "section": "VI", "title": "Умышленное нанесение побоев", "penalty": "от 1 до 3 лет", "stars": "★★★", "note": ""},
    {"article": "6.2", "section": "VI", "title": "Убийство", "penalty": "от 2 до 4 лет", "stars": "★★★★", "note": ""},
    {"article": "6.3", "section": "VI", "title": "Тяжкое убийство", "penalty": "от 4 до 5 лет", "stars": "★★★★★", "note": ""},
    {"article": "6.4", "section": "VI", "title": "Угроза убийством", "penalty": "от 2 до 3 лет или штраф $30.000-$50.000", "stars": "★★★", "note": ""},
    {"article": "7.1", "section": "VII", "title": "Похищение человека", "penalty": "от 4 до 5 лет", "stars": "★★★★★", "note": ""},
    {"article": "7.4", "section": "VII", "title": "Клевета", "penalty": "от 2 до 3 лет или штраф $40.000-$80.000", "stars": "★★★", "note": ""},
    {"article": "8.1", "section": "VIII", "title": "Изнасилование", "penalty": "от 3 до 4 лет", "stars": "★★★★", "note": ""},
    {"article": "10.1", "section": "X", "title": "Кража", "penalty": "от 2 до 3 лет", "stars": "★★★", "note": ""},
    {"article": "10.2", "section": "X", "title": "Мошенничество", "penalty": "от 2 до 3 лет", "stars": "★★★", "note": ""},
    {"article": "10.3", "section": "X", "title": "Грабеж", "penalty": "от 2 до 3 лет", "stars": "★★★", "note": ""},
    {"article": "10.4", "section": "X", "title": "Разбой", "penalty": "от 2 до 4 лет", "stars": "★★★★", "note": ""},
    {"article": "10.5", "section": "X", "title": "Угон авто", "penalty": "от 1 до 3 лет", "stars": "★★★", "note": ""},
    {"article": "10.9", "section": "X", "title": "Проникновение в жилище", "penalty": "от 3 до 4 лет", "stars": "★★★★", "note": ""},
    {"article": "11.3", "section": "XI", "title": "Уклонение от налогов", "penalty": "взыскание ×2 + от 3 до 5 лет", "stars": "★★★★★", "note": ""},
    {"article": "12.1", "section": "XII", "title": "Терроризм", "penalty": "от 4 до 5 лет", "stars": "★★★★★", "note": ""},
    {"article": "12.8", "section": "XII", "title": "Хранение оружия", "penalty": "от 3 до 4 лет или штраф $20.000-$60.000", "stars": "★★★★", "note": ""},
    {"article": "12.14", "section": "XII", "title": "Хулиганство", "penalty": "до 2 лет или штраф $30.000-$40.000", "stars": "★★", "note": ""},
    {"article": "13.2", "section": "XIII", "title": "Сбыт наркотиков", "penalty": "от 3 до 5 лет", "stars": "★★★★★", "note": ""},
    {"article": "13.3", "section": "XIII", "title": "Хранение наркотиков", "penalty": "от 2 до 4 лет", "stars": "★★★★", "note": ""},
    {"article": "15.4", "section": "XV", "title": "Получение взятки", "penalty": "от 4 до 5 лет", "stars": "★★★★★", "note": ""},
    {"article": "15.5", "section": "XV", "title": "Дача взятки", "penalty": "от 4 до 5 лет", "stars": "★★★★★", "note": ""},
    {"article": "15.7", "section": "XV", "title": "Деструктивное поведение", "penalty": "штраф $30.000-$70.000 или до 3 лет", "stars": "★★★", "note": ""},
    {"article": "16.15", "section": "XVI", "title": "Побег из тюрьмы", "penalty": "от 1 до 5 лет", "stars": "★..★★★★★", "note": ""},
    {"article": "17.1", "section": "XVII", "title": "Посягательство на жизнь полицейского", "penalty": "от 4 до 5 лет", "stars": "★★★★★", "note": ""},
    {"article": "17.3", "section": "XVII", "title": "Оскорбление полицейского", "penalty": "штраф $20.000-$50.000 или до 3 лет", "stars": "★★★", "note": ""},
    {"article": "19.1", "section": "XIX", "title": "Браконьерство", "penalty": "от 1 до 3 лет", "stars": "★★★", "note": ""},
]

# ========== БАЗА ПК ==========
pk_sections = {
    "I": "Основные положения",
    "II": "Доказательства и доказывание",
    "III": "Меры процессуального принуждения",
    "IV": "Иные положения",
    "V": "Ходатайства и жалобы",
    "VI": "Следствие",
    "VII": "Уголовное производство",
}

pk_laws = [
    {"article": "3", "section": "I", "title": "Уважение чести и достоинства", "penalty": "Запрещены унижение, пытки", "stars": "⚖️", "note": ""},
    {"article": "15", "section": "III", "title": "Срок задержания", "penalty": "Максимум 1 час", "stars": "⏰", "note": ""},
    {"article": "16", "section": "III", "title": "Основания задержания", "penalty": "8 оснований", "stars": "🔍", "note": ""},
    {"article": "17", "section": "III", "title": "Порядок задержания", "penalty": "11 шагов", "stars": "📋", "note": ""},
    {"article": "19", "section": "III", "title": "Задержание госслужащего", "penalty": "Уведомить руководство", "stars": "👮", "note": ""},
    {"article": "20", "section": "III", "title": "Освобождение", "penalty": "7 оснований", "stars": "🔓", "note": ""},
    {"article": "22", "section": "III", "title": "Права задержанного", "penalty": "5 прав", "stars": "📜", "note": ""},
    {"article": "28", "section": "III", "title": "Личный обыск", "penalty": "Только при задержании", "stars": "🔎", "note": ""},
    {"article": "29", "section": "III", "title": "Обыск транспорта", "penalty": "Обыск с ордером", "stars": "🚗", "note": ""},
    {"article": "31", "section": "IV", "title": "Видеофиксация", "penalty": "Обязательная запись", "stars": "🎥", "note": ""},
    {"article": "33", "section": "IV", "title": "Залог", "penalty": "от $25.000 + $25.000 за звезду", "stars": "💰", "note": ""},
    {"article": "36", "section": "IV", "title": "Применение силы", "penalty": "5 стадий", "stars": "💪", "note": ""},
    {"article": "9", "section": "V", "title": "Обжалование", "penalty": "48 часов", "stars": "📋", "note": ""},
    {"article": "12", "section": "II", "title": "Недопустимые доказательства", "penalty": "Показания до прав", "stars": "🚫", "note": ""},
    {"article": "56", "section": "VI", "title": "Адвокат на допросе", "penalty": "Присутствует", "stars": "👨‍⚖️", "note": ""},
    {"article": "М7", "section": "III", "title": "Правило Миранды", "penalty": "Право молчать", "stars": "📢", "note": ""},
]

# ========== ФУНКЦИЯ ДЛЯ ИИ ==========
async def ask_ai(question: str) -> str:
    try:
        uk_context = "\n".join([f"Ст.{l['article']}: {l['title']} — {l['penalty']}" for l in uk_laws[:20]])
        pk_context = "\n".join([f"Ст.{p['article']}: {p['title']} — {p['penalty']}" for p in pk_laws])
        
        prompt = f"""Ты — юридический помощник в игре Majestic RP. Отвечай на вопросы по УК и ПК штата Сан-Андреас.
Кратко (2-4 предложения), по делу, ссылайся на статьи.

УК: {uk_context}
ПК: {pk_context}

Вопрос: {question}"""
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"❌ Ошибка ИИ: {str(e)}"

# ========== ПОИСК ==========
def smart_search(query: str, database: list):
    query_lower = query.lower().strip()
    found = []
    
    match_num = re.search(r'(\d{1,2}(?:\.\d{1,2})?)', query_lower)
    if match_num:
        art_num = match_num.group(1)
        for law in database:
            if law["article"] == art_num:
                return [law]
    
    for law in database:
        if (law["title"].lower() in query_lower or query_lower in law["title"].lower() or
            law["penalty"].lower() in query_lower or query_lower in law["penalty"].lower()):
            found.append(law)
    
    if not found:
        all_texts = []
        for law in database:
            all_texts.append(law["title"].lower())
            all_texts.append(law["penalty"].lower())
        matches = get_close_matches(query_lower, all_texts, n=3, cutoff=0.5)
        for match in matches:
            for law in database:
                if match == law["title"].lower() or match == law["penalty"].lower():
                    if law not in found:
                        found.append(law)
    return found

# ========== СОБЫТИЕ ==========
@bot.event
async def on_ready():
    cleanup_expired()
    
    stats = get_premium_stats()
    print(f"✅ Бот {bot.user} готов!")
    print(f"📜 УК: {len(uk_laws)} статей | ПК: {len(pk_laws)} статей")
    print(f"💎 Бесплатно: 5 + бонусы | Премиум: от 55 ₽")
    print(f"📊 Статистика: {stats['total_users']} пользователей, {stats['active_premium']} активных")
    
    try:
        synced = await bot.tree.sync()
        print(f"🔗 Синхронизировано {len(synced)} слэш-команд")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    
    Thread(target=run_web_server, daemon=True).start()
    print("🌐 Веб-сервер запущен")

# ========== ОСНОВНЫЕ КОМАНДЫ ==========

@bot.tree.command(name="купить", description="Купить премиум (выберите срок)")
async def buy_premium(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    embed = discord.Embed(
        title="💎 Выберите срок подписки",
        description=(
            "Нажмите на кнопку с нужным сроком:\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "**📌 Ваш Discord ID:** `" + user_id + "`\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "**Как получить ID:**\n"
            "• ПК: Настройки → Дополнительно → Режим разработчика → ПКМ по имени → Копировать ID\n"
            "• Телефон: Настройки → Внешний вид → Режим разработчика → Удерживать палец на имени → Копировать ID"
        ),
        color=discord.Color.gold()
    )
    view = PremiumDurationView(user_id)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

@bot.tree.command(name="give_premium", description="[АДМИН] Выдать премиум")
@app_commands.describe(user="Пользователь", days="Количество дней")
async def give_premium(interaction: discord.Interaction, user: discord.User, days: int = 30):
    if not (is_owner(interaction) or interaction.user.guild_permissions.administrator):
        await interaction.response.send_message("❌ Нет прав!", ephemeral=True)
        return
    
    new_expiry = add_premium(str(user.id), days)
    await interaction.response.send_message(f"✅ {user.mention} получил премиум на {days} дней!\n📅 До: {new_expiry.strftime('%d.%m.%Y')}")

@bot.tree.command(name="premium_list", description="[АДМИН] Список активных подписок")
async def premium_list(interaction: discord.Interaction):
    if not (is_owner(interaction) or interaction.user.guild_permissions.administrator):
        await interaction.response.send_message("❌ Нет прав!", ephemeral=True)
        return
    
    users = get_all_premium_users()
    if not users:
        await interaction.response.send_message("Нет активных подписок.", ephemeral=True)
        return
    
    embed = discord.Embed(title=f"💎 Активные подписки ({len(users)})", color=discord.Color.green())
    for u in users[:20]:
        try:
            user = await bot.fetch_user(int(u["id"]))
            name = user.name
        except:
            name = f"ID: {u['id']}"
        days_left = (u["expires_date"] - datetime.now()).days
        embed.add_field(name=name, value=f"До: {u['expires_date'].strftime('%d.%m.%Y')} ({days_left} дн.)", inline=False)
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="premium_stats", description="[АДМИН] Статистика")
async def premium_stats(interaction: discord.Interaction):
    if not (is_owner(interaction) or interaction.user.guild_permissions.administrator):
        await interaction.response.send_message("❌ Нет прав!", ephemeral=True)
        return
    
    stats = get_premium_stats()
    await interaction.response.send_message(
        f"📊 **Статистика**\n👥 Всего: {stats['total_users']}\n💎 Активных: {stats['active_premium']}\n📅 Месяц: {stats['month']}",
        ephemeral=True
    )

@bot.tree.command(name="premium_status", description="Проверить статус подписки")
async def premium_status(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    premium = is_premium(user_id)
    used = get_user_requests(user_id)
    bonus = get_bonus_requests(user_id)
    total = 5 + bonus
    remaining = total - used
    
    if premium:
        expire = get_premium_expiry(user_id)
        expire_date = datetime.fromisoformat(expire)
        await interaction.response.send_message(
            f"💎 **Премиум активен**\n📅 До: {expire_date.strftime('%d.%m.%Y')}\n📊 Запросов: {used}/{total}",
            ephemeral=True
        )
    else:
        await interaction.response.send_message(
            f"❌ **Премиум не активен**\n📊 Запросов: {used}/{total} осталось {remaining}\n🎁 Бонусов: +{bonus}\n💰 Купить: `/купить`\n🌟 Рефералы: `/реф`",
            ephemeral=True
        )

@bot.tree.command(name="ук", description="Поиск по УК")
@app_commands.describe(query="Номер или название")
async def uk_slash(interaction: discord.Interaction, query: str):
    user_id = str(interaction.user.id)
    
    if not is_premium(user_id) and get_remaining_free_requests(user_id) <= 0:
        await interaction.response.send_message("⚠️ Лимит исчерпан! Купите премиум: `/купить`", ephemeral=True)
        return
    
    await interaction.response.defer()
    results = smart_search(query, uk_laws)
    
    if not results:
        await interaction.followup.send(f"❌ Ничего не найдено по `{query}`")
        return
    
    if not is_premium(user_id):
        increment_requests(user_id)
        used = get_user_requests(user_id)
        bonus = get_bonus_requests(user_id)
        await interaction.followup.send(f"📊 Использовано: {used}/{5+bonus}")
    
    if len(results) > 1:
        embed = discord.Embed(title=f"🔍 Найдено {len(results)} статей", color=discord.Color.orange())
        for law in results[:5]:
            section_name = uk_sections.get(law["section"], "Общая часть")
            embed.add_field(name=f"Ст.{law['article']}", value=f"{law['title']}\n{section_name}", inline=False)
        await interaction.followup.send(embed=embed)
        return
    
    law = results[0]
    section_name = uk_sections.get(law["section"], "Общая часть")
    embed = discord.Embed(title=f"⚖️ Ст {law['article']} УК", description=f"**{law['title']}**\n📌 {section_name}\n{law['stars']}", color=discord.Color.red())
    embed.add_field(name="📝 Наказание", value=law['penalty'], inline=False)
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="пк", description="Поиск по ПК")
@app_commands.describe(query="Номер или тема")
async def pk_slash(interaction: discord.Interaction, query: str):
    user_id = str(interaction.user.id)
    
    if not is_premium(user_id) and get_remaining_free_requests(user_id) <= 0:
        await interaction.response.send_message("⚠️ Лимит исчерпан! Купите премиум: `/купить`", ephemeral=True)
        return
    
    await interaction.response.defer()
    results = smart_search(query, pk_laws)
    
    if not results:
        await interaction.followup.send(f"❌ Ничего не найдено по `{query}`")
        return
    
    if not is_premium(user_id):
        increment_requests(user_id)
        used = get_user_requests(user_id)
        bonus = get_bonus_requests(user_id)
        await interaction.followup.send(f"📊 Использовано: {used}/{5+bonus}")
    
    if len(results) > 1:
        embed = discord.Embed(title=f"🔍 Найдено {len(results)} статей", color=discord.Color.green())
        for law in results[:5]:
            section_name = pk_sections.get(law["section"], "Общая часть")
            embed.add_field(name=f"Ст.{law['article']}", value=f"{law['title']}\n{section_name}", inline=False)
        await interaction.followup.send(embed=embed)
        return
    
    law = results[0]
    section_name = pk_sections.get(law["section"], "Общая часть")
    embed = discord.Embed(title=f"📜 Ст {law['article']} ПК", description=f"**{law['title']}**\n📌 {section_name}\n{law['stars']}", color=discord.Color.green())
    embed.add_field(name="📝 Содержание", value=law['penalty'], inline=False)
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="вопрос", description="Задать вопрос ИИ-адвокату")
@app_commands.describe(question="Ваш вопрос")
async def ask_question(interaction: discord.Interaction, question: str):
    user_id = str(interaction.user.id)
    
    if not is_premium(user_id) and get_remaining_free_requests(user_id) <= 0:
        await interaction.response.send_message("⚠️ Лимит исчерпан! Купите премиум: `/купить`", ephemeral=True)
        return
    
    await interaction.response.defer()
    
    if not is_premium(user_id):
        increment_requests(user_id)
        used = get_user_requests(user_id)
        bonus = get_bonus_requests(user_id)
        await interaction.followup.send(f"📊 Использовано: {used}/{5+bonus}")
    
    answer = await ask_ai(question)
    embed = discord.Embed(title="⚖️ ИИ-адвокат", description=answer, color=discord.Color.purple())
    await interaction.edit_original_response(content=None, embed=embed)

@bot.tree.command(name="разделы_ук", description="Разделы УК")
async def uk_sections_cmd(interaction: discord.Interaction):
    embed = discord.Embed(title="📚 Разделы УК", color=discord.Color.red())
    for num, name in uk_sections.items():
        count = len([l for l in uk_laws if l["section"] == num])
        embed.add_field(name=f"Глава {num}", value=f"{name}\n└ {count} статей", inline=True)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="разделы_пк", description="Разделы ПК")
async def pk_sections_cmd(interaction: discord.Interaction):
    embed = discord.Embed(title="📚 Разделы ПК", color=discord.Color.green())
    for num, name in pk_sections.items():
        count = len([l for l in pk_laws if l["section"] == num])
        embed.add_field(name=f"Раздел {num}", value=f"{name}\n└ {count} статей", inline=True)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="реф", description="Реферальная программа")
async def ref_menu(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    code = get_user_ref_code(user_id)
    
    embed = discord.Embed(
        title="🌟 Реферальная программа",
        description=(
            f"**Ваш код:** `{code}`\n\n"
            "**Награды:**\n"
            "• Приглашённый: +5 запросов\n"
            "• Пригласивший: +14 дней премиума\n\n"
            "**Команды:**\n"
            "• `/код` — показать код\n"
            "• `/активировать_код КОД` — активировать код\n"
            "• `/статистика` — ваша статистика"
        ),
        color=discord.Color.gold()
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="код", description="Показать реферальный код")
async def ref_code(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    code = get_user_ref_code(user_id)
    await interaction.response.send_message(f"🔑 Ваш код: `{code}`", ephemeral=True)

@bot.tree.command(name="активировать_код", description="Активировать реферальный код друга")
@app_commands.describe(code="Реферальный код")
async def ref_activate(interaction: discord.Interaction, code: str):
    user_id = str(interaction.user.id)
    
    own_code = get_user_ref_code(user_id)
    if code.upper() == own_code:
        await interaction.response.send_message("❌ Нельзя активировать свой код!", ephemeral=True)
        return
    
    referrer_id = get_user_by_ref_code(code)
    if not referrer_id:
        await interaction.response.send_message(f"❌ Код `{code}` не найден!", ephemeral=True)
        return
    
    success = add_referral(user_id, referrer_id)
    if not success:
        await interaction.response.send_message("❌ Вы уже активировали чей-то код!", ephemeral=True)
        return
    
    await interaction.response.send_message(f"✅ Код активирован! Вы получили +5 запросов!", ephemeral=True)
    
    try:
        owner = await bot.fetch_user(int(referrer_id))
        if owner:
            await owner.send(f"🎉 {interaction.user.mention} активировал ваш код! Вы получили +14 дней премиума!")
    except:
        pass

@bot.tree.command(name="статистика", description="Реферальная статистика")
async def ref_stats(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    stats = get_referral_stats(user_id)
    bonus = get_bonus_requests(user_id)
    code = get_user_ref_code(user_id)
    
    await interaction.response.send_message(
        f"📊 **Реферальная статистика**\n🔑 Код: `{code}`\n👥 Приглашено: {stats['count']}\n🎁 Бонусов: +{bonus}",
        ephemeral=True
    )

@bot.tree.command(name="поддержка", description="Связаться с поддержкой")
@app_commands.describe(вопрос="Ваш вопрос")
async def support_command(interaction: discord.Interaction, вопрос: str):
    owner = await bot.fetch_user(OWNER_ID)
    if owner:
        embed = discord.Embed(
            title="🆘 Обращение",
            description=f"**От:** {interaction.user.mention}\n**Вопрос:**\n{вопрос}",
            color=discord.Color.red(),
            timestamp=datetime.now()
        )
        await owner.send(embed=embed)
    await interaction.response.send_message("✅ Запрос отправлен!", ephemeral=True)

@bot.tree.command(name="справка", description="Все команды")
async def help_slash(interaction: discord.Interaction):
    embed = discord.Embed(title="📚 Помощь", color=discord.Color.gold())
    embed.add_field(name="⚖️ УК/ПК", value="`/ук`, `/пк`, `/разделы_ук`, `/разделы_пк`", inline=False)
    embed.add_field(name="🤖 ИИ", value="`/вопрос`", inline=False)
    embed.add_field(name="💎 Премиум", value="`/купить`, `/premium_status`", inline=False)
    embed.add_field(name="🌟 Рефералы", value="`/реф`, `/код`, `/активировать_код`, `/статистика`", inline=False)
    embed.add_field(name="🆘 Другое", value="`/поддержка`, `/справка`", inline=False)
    embed.add_field(name="👑 Админ", value="`/give_premium`, `/premium_list`, `/premium_stats`", inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="инфо", description="О боте")
async def info_slash(interaction: discord.Interaction):
    stats = get_premium_stats()
    embed = discord.Embed(title="📚 Юридический помощник Majestic RP", color=discord.Color.gold())
    embed.add_field(name="💎 Бесплатно", value="5 запросов + бонусы", inline=False)
    embed.add_field(name="💰 Премиум", value="30д — 55 ₽ | 365д — 660 ₽", inline=False)
    embed.add_field(name="🌟 Рефералы", value="+14 дней пригласившему, +5 запросов другу", inline=False)
    embed.add_field(name="📊 Статистика", value=f"👥 {stats['total_users']} | 💎 {stats['active_premium']}", inline=False)
    await interaction.response.send_message(embed=embed)

@bot.command(name="вопрос")
async def ask_prefix(ctx, *, question: str):
    user_id = str(ctx.author.id)
    
    if not is_premium(user_id) and get_remaining_free_requests(user_id) <= 0:
        await ctx.send("⚠️ Лимит исчерпан! Купите премиум: `/купить`")
        return
    
    async with ctx.typing():
        if not is_premium(user_id):
            increment_requests(user_id)
        answer = await ask_ai(question)
        embed = discord.Embed(title="⚖️ ИИ-адвокат", description=answer, color=discord.Color.blue())
        await ctx.send(embed=embed)

# ===== ЗАПУСК =====
bot.run(TOKEN)
