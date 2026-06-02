import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View
import re
import os
import json
import asyncio
from datetime import datetime, timedelta
from difflib import get_close_matches
from threading import Thread
from flask import Flask
import google.generativeai as genai

# ===== ВЕБ-СЕРВЕР =====
app = Flask(__name__)

@app.route('/')
def health_check():
    return "✅ Bot is alive!", 200

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

# ========== КНОПКИ ВЫБОРА СРОКА ПОДПИСКИ ==========
class PremiumDurationView(View):
    """Кнопки выбора срока подписки"""
    def __init__(self, user_id: str):
        super().__init__(timeout=120)
        self.user_id = user_id
    
    @discord.ui.button(label="30 дней - 55 ₽", style=discord.ButtonStyle.green, emoji="💎", row=0)
    async def premium_30(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_payment(interaction, 30, 55)
    
    @discord.ui.button(label="60 дней - 110 ₽", style=discord.ButtonStyle.blurple, emoji="💎", row=0)
    async def premium_60(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_payment(interaction, 60, 110)
    
    @discord.ui.button(label="90 дней - 165 ₽", style=discord.ButtonStyle.blurple, emoji="💎", row=1)
    async def premium_90(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_payment(interaction, 90, 165)
    
    @discord.ui.button(label="180 дней - 330 ₽", style=discord.ButtonStyle.blurple, emoji="💎", row=1)
    async def premium_180(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_payment(interaction, 180, 330)
    
    @discord.ui.button(label="365 дней - 660 ₽", style=discord.ButtonStyle.blurple, emoji="👑", row=2)
    async def premium_365(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_payment(interaction, 365, 660)
    
    async def process_payment(self, interaction: discord.Interaction, days: int, price: int):
        user_id = str(interaction.user.id)
        
        embed = discord.Embed(
            title=f"💎 Подписка на {days} дней — {price} ₽",
            description=(
                f"🔥 **Что даёт премиум:**\n"
                f"• Безлимитные запросы к боту\n"
                f"• Приоритетная поддержка\n\n"
                f"💳 **Как оплатить:**\n"
                f"1. Переведите **{price} ₽** на карту [2200 2492 0252 2980]\n"
                f"2. **В комментарии к переводу укажите:**\n"
                f"   `!премиум {user_id} {days}`\n"
                f"3. После оплаты напишите боту в ЛС:\n"
                f"   `/активировать {user_id} {days}`\n\n"
                f"📌 **Проверить статус:** `/premium_status`"
            ),
            color=discord.Color.gold()
        )
        await interaction.response.edit_message(content=None, embed=embed, view=None)

# ========== СИСТЕМА ПОДПИСКИ (5 пробных запросов в месяц) ==========
DATA_FILE = "premium_users.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def get_user_requests(user_id: str) -> int:
    data = load_data()
    current_month = datetime.now().strftime("%Y-%m")
    
    if user_id not in data:
        data[user_id] = {"requests": 0, "month": current_month, "premium_until": None}
    
    if data[user_id].get("month") != current_month:
        data[user_id]["requests"] = 0
        data[user_id]["month"] = current_month
    
    save_data(data)
    return data[user_id]["requests"]

def increment_requests(user_id: str) -> int:
    data = load_data()
    current_month = datetime.now().strftime("%Y-%m")
    
    if user_id not in data:
        data[user_id] = {"requests": 0, "month": current_month, "premium_until": None}
    
    if data[user_id].get("month") != current_month:
        data[user_id]["requests"] = 0
        data[user_id]["month"] = current_month
    
    data[user_id]["requests"] += 1
    save_data(data)
    return data[user_id]["requests"]

def is_premium(user_id: str) -> bool:
    data = load_data()
    if user_id not in data:
        return False
    
    premium_until = data[user_id].get("premium_until")
    if not premium_until:
        return False
    
    expire_date = datetime.fromisoformat(premium_until)
    if expire_date <= datetime.now():
        data[user_id]["premium_until"] = None
        save_data(data)
        return False
    
    return True

def add_premium(user_id: str, days: int):
    data = load_data()
    current_month = datetime.now().strftime("%Y-%m")
    
    if user_id not in data:
        data[user_id] = {"requests": 0, "month": current_month, "premium_until": None}
    
    current_expiry = data[user_id].get("premium_until")
    if current_expiry:
        new_expiry = datetime.fromisoformat(current_expiry) + timedelta(days=days)
    else:
        new_expiry = datetime.now() + timedelta(days=days)
    
    data[user_id]["premium_until"] = new_expiry.isoformat()
    save_data(data)
    print(f"💎 Премиум выдан {user_id} на {days} дней до {new_expiry.strftime('%Y-%m-%d')}")

def get_premium_expiry(user_id: str) -> str:
    data = load_data()
    if user_id not in data:
        return None
    return data[user_id].get("premium_until")

def get_remaining_free_requests(user_id: str) -> int:
    used = get_user_requests(user_id)
    return max(0, 5 - used)

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
    print(f"✅ Бот {bot.user} готов!")
    print(f"📜 УК: {len(uk_laws)} статей | ПК: {len(pk_laws)} статей")
    print(f"💎 Бесплатно: 5 пробных запросов в месяц | Премиум: от 55 ₽")
    print(f"👑 Владелец бота: {OWNER_ID}")
    
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
            "**📌 Как получить свой Discord ID:**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "**🖥️ На компьютере:**\n"
            "1. Нажмите на шестерёнку (⚙️) рядом с вашим именем\n"
            "2. Выберите **«Дополнительно»** (Advanced)\n"
            "3. Включите **«Режим разработчика»** (Developer Mode)\n"
            "4. Нажмите правой кнопкой мыши по своему имени\n"
            "5. Выберите **«Копировать ID»**\n\n"
            "**📱 На телефоне:**\n"
            "1. Нажмите на свою аватарку в правом нижнем углу\n"
            "2. Выберите **«Внешний вид»** (Appearance)\n"
            "3. Включите **«Режим разработчика»** (Developer Mode)\n"
            "4. Удерживайте палец на своём имени\n"
            "5. Выберите **«Копировать ID»**\n\n"
            "**✅ Ваш ID:** `" + user_id + "`\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        ),
        color=discord.Color.gold()
    )
    view = PremiumDurationView(user_id)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

@bot.tree.command(name="активировать", description="Активировать премиум после оплаты")
@app_commands.describe(id="Ваш Discord ID", days="Количество дней (30, 60, 90, 180, 365)")
async def activate_premium(interaction: discord.Interaction, id: str, days: int = 30):
    user_id = str(interaction.user.id)
    
    if id != user_id:
        embed = discord.Embed(title="❌ Ошибка!", description="Вы указали чужой Discord ID.", color=discord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    valid_days = [30, 60, 90, 180, 365]
    if days not in valid_days:
        embed = discord.Embed(title="❌ Неверный срок", description=f"Выберите: {', '.join(str(d) for d in valid_days)} дней", color=discord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    price = days * 55 // 30
    
    owner = await bot.fetch_user(OWNER_ID)
    if owner:
        embed_owner = discord.Embed(
            title="🆕 Запрос на активацию премиума!",
            description=f"**Пользователь:** {interaction.user.mention}\n**ID:** `{user_id}`\n**Срок:** `{days} дней`\n**Сумма:** `{price} ₽`",
            color=discord.Color.orange(),
            timestamp=datetime.now()
        )
        await owner.send(embed=embed_owner)
        await owner.send(f"✅ Выдайте премиум: `/give_premium {user_id} {days}`")
    
    embed = discord.Embed(
        title="✅ Запрос отправлен!",
        description=f"Запрос на {days} дней отправлен владельцу.\nСумма: {price} ₽\n\nСтатус: `/premium_status`",
        color=discord.Color.green()
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="give_premium", description="[АДМИН] Выдать премиум")
@app_commands.describe(user="Пользователь", days="Количество дней")
async def give_premium(interaction: discord.Interaction, user: discord.User, days: int = 30):
    if not (is_owner(interaction) or interaction.user.guild_permissions.administrator):
        embed = discord.Embed(title="❌ Нет прав!", color=discord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    add_premium(str(user.id), days)
    embed = discord.Embed(title="✅ Премиум выдан!", description=f"{user.mention} получил премиум на **{days}** дней.", color=discord.Color.green())
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="premium_status", description="Проверить статус подписки")
async def premium_status(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    premium = is_premium(user_id)
    used = get_user_requests(user_id)
    remaining = 5 - used
    
    if premium:
        expire = get_premium_expiry(user_id)
        embed = discord.Embed(
            title="💎 Статус подписки",
            description=f"✅ Премиум **активен**\n📅 Действует до: {expire[:10]}\n📊 Пробных запросов: {used}/5",
            color=discord.Color.green()
        )
    else:
        embed = discord.Embed(
            title="💎 Статус подписки",
            description=f"❌ Премиум **не активен**\n\n📊 Пробных запросов: {used}/5 осталось {remaining}\n💰 Премиум: `/купить`",
            color=discord.Color.orange()
        )
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="ук", description="Поиск по Уголовному кодексу")
@app_commands.describe(query="Номер статьи или название")
async def uk_slash(interaction: discord.Interaction, query: str):
    user_id = str(interaction.user.id)
    
    if not is_premium(user_id) and get_remaining_free_requests(user_id) <= 0:
        embed = discord.Embed(title="⚠️ Лимит исчерпан", description="Купите премиум: `/купить`", color=discord.Color.orange())
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    await interaction.response.defer()
    results = smart_search(query, uk_laws)
    
    if not results:
        await interaction.followup.send(f"❌ Ничего не найдено по `{query}`")
        return
    
    if not is_premium(user_id):
        increment_requests(user_id)
        used = get_user_requests(user_id)
        await interaction.followup.send(f"📊 Пробных запросов использовано: {used}/5")
    
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

@bot.tree.command(name="пк", description="Поиск по Процессуальному кодексу")
@app_commands.describe(query="Номер статьи или тема")
async def pk_slash(interaction: discord.Interaction, query: str):
    user_id = str(interaction.user.id)
    
    if not is_premium(user_id) and get_remaining_free_requests(user_id) <= 0:
        embed = discord.Embed(title="⚠️ Лимит исчерпан", description="Купите премиум: `/купить`", color=discord.Color.orange())
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    await interaction.response.defer()
    results = smart_search(query, pk_laws)
    
    if not results:
        await interaction.followup.send(f"❌ Ничего не найдено по `{query}`")
        return
    
    if not is_premium(user_id):
        increment_requests(user_id)
        used = get_user_requests(user_id)
        await interaction.followup.send(f"📊 Пробных запросов использовано: {used}/5")
    
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
@app_commands.describe(question="Ваш вопрос по УК или ПК")
async def ask_question(interaction: discord.Interaction, question: str):
    user_id = str(interaction.user.id)
    
    if not is_premium(user_id) and get_remaining_free_requests(user_id) <= 0:
        embed = discord.Embed(title="⚠️ Лимит исчерпан", description="Купите премиум: `/купить`", color=discord.Color.orange())
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    await interaction.response.defer()
    
    if not is_premium(user_id):
        increment_requests(user_id)
        used = get_user_requests(user_id)
        await interaction.followup.send(f"📊 Пробных запросов использовано: {used}/5")
    
    answer = await ask_ai(question)
    embed = discord.Embed(title="⚖️ ИИ-адвокат", description=answer, color=discord.Color.purple())
    await interaction.edit_original_response(content=None, embed=embed)

@bot.tree.command(name="разделы_ук", description="Показать разделы УК")
async def uk_sections_cmd(interaction: discord.Interaction):
    embed = discord.Embed(title="📚 Разделы УК", color=discord.Color.red())
    for num, name in uk_sections.items():
        count = len([l for l in uk_laws if l["section"] == num])
        embed.add_field(name=f"Глава {num}", value=f"{name}\n└ {count} статей", inline=True)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="разделы_пк", description="Показать разделы ПК")
async def pk_sections_cmd(interaction: discord.Interaction):
    embed = discord.Embed(title="📚 Разделы ПК", color=discord.Color.green())
    for num, name in pk_sections.items():
        count = len([l for l in pk_laws if l["section"] == num])
        embed.add_field(name=f"Раздел {num}", value=f"{name}\n└ {count} статей", inline=True)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="поддержка", description="Связаться с поддержкой")
@app_commands.describe(вопрос="Ваш вопрос")
async def support_command(interaction: discord.Interaction, вопрос: str):
    user = interaction.user
    
    owner = await bot.fetch_user(OWNER_ID)
    if owner:
        embed = discord.Embed(
            title="🆘 Обращение в поддержку",
            description=f"**От:** {user.mention}\n**ID:** `{user.id}`\n\n**Вопрос:**\n{вопрос}",
            color=discord.Color.red(),
            timestamp=datetime.now()
        )
        await owner.send(embed=embed)
    
    embed = discord.Embed(title="✅ Запрос отправлен!", description="Владелец бота свяжется с вами.", color=discord.Color.green())
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="справка", description="Показать все команды")
async def help_slash(interaction: discord.Interaction):
    embed = discord.Embed(title="📚 Помощь", color=discord.Color.gold())
    embed.add_field(name="⚖️ УК", value="`/ук убийство`", inline=False)
    embed.add_field(name="📜 ПК", value="`/пк задержание`", inline=False)
    embed.add_field(name="🤖 ИИ", value="`/вопрос Твой вопрос`", inline=False)
    embed.add_field(name="📚 Разделы", value="`/разделы_ук`, `/разделы_пк`", inline=False)
    embed.add_field(name="💎 Подписка", value="`/купить`, `/активировать`, `/premium_status`, `/инфо`", inline=False)
    embed.add_field(name="🆘 Поддержка", value="`/поддержка Твой вопрос`", inline=False)
    embed.add_field(name="👑 Админ", value="`/give_premium @user 30`", inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="инфо", description="Информация о боте")
async def info_slash(interaction: discord.Interaction):
    embed = discord.Embed(title="📚 Юридический помощник Majestic RP", color=discord.Color.gold())
    embed.add_field(name="💎 Бесплатно", value="5 пробных запросов в месяц", inline=False)
    embed.add_field(name="💰 Премиум", value="30 дней — 55 ₽ | 60 дней — 110 ₽ | 90 дней — 165 ₽ | 180 дней — 330 ₽ | 365 дней — 660 ₽", inline=False)
    embed.add_field(name="🔗 Команды", value="`/купить`, `/premium_status`, `/справка`", inline=False)
    await interaction.response.send_message(embed=embed)

# Префиксная команда
@bot.command(name="вопрос")
async def ask_prefix(ctx, *, question: str):
    user_id = str(ctx.author.id)
    
    if not is_premium(user_id) and get_remaining_free_requests(user_id) <= 0:
        embed = discord.Embed(title="⚠️ Лимит исчерпан", description="Купите премиум: `/купить`", color=discord.Color.orange())
        await ctx.send(embed=embed)
        return
    
    async with ctx.typing():
        if not is_premium(user_id):
            increment_requests(user_id)
        answer = await ask_ai(question)
        embed = discord.Embed(title="⚖️ ИИ-адвокат", description=answer, color=discord.Color.blue())
        await ctx.send(embed=embed)

# ===== ЗАПУСК =====
bot.run(TOKEN)
