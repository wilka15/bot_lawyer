import discord
from discord.ext import commands
from discord import app_commands
import re
import os
import json
import hashlib
import hmac
from datetime import datetime, timedelta
from difflib import get_close_matches
from threading import Thread
from flask import Flask, request, jsonify
import google.generativeai as genai
import requests

# ===== ВЕБ-СЕРВЕР ДЛЯ RENDER И ПЛАТЕЖЕЙ =====
app = Flask(__name__)

@app.route('/')
def health_check():
    return "✅ Bot is alive!", 200

# Эндпоинт для вебхука от DonationAlerts
@app.route('/webhook/donationalerts', methods=['POST'])
def donationalerts_webhook():
    """Обработка платежей с DonationAlerts"""
    # Получаем данные
    data = request.json
    
    # Проверяем подпись (для безопасности)
    signature = request.headers.get('Authorization', '').replace('Bearer ', '')
    if signature != os.environ.get("DONATIONALERTS_SECRET"):
        return jsonify({"status": "unauthorized"}), 401
    
    # Проверяем, что это успешная оплата
    if data.get('event_type') == 'donation':
        amount = float(data.get('data', {}).get('amount', 0))
        username = data.get('data', {}).get('username', '')
        message = data.get('data', {}).get('message', '')
        
        # Проверяем сумму (60 ₽ или больше)
        if amount >= 60:
            # Из сообщения пытаемся достать Discord ID
            # Пример сообщения: "!премиум 123456789012345678"
            discord_id = None
            if message.startswith('!премиум'):
                parts = message.split()
                if len(parts) > 1 and parts[1].isdigit():
                    discord_id = parts[1]
            
            if discord_id:
                # Выдаём премиум на 30 дней
                add_premium(discord_id, 30)
                print(f"✅ Выдан премиум пользователю {discord_id} на 30 дней (оплата {amount} ₽)")
                
                # Отправляем уведомление в Discord
                channel_id = os.environ.get("DISCORD_LOG_CHANNEL")
                if channel_id:
                    channel = bot.get_channel(int(channel_id))
                    if channel:
                        asyncio.create_task(channel.send(f"💎 Пользователь <@{discord_id}> приобрёл премиум на 30 дней! Спасибо за поддержку!"))
                
                return jsonify({"status": "ok"}), 200
    
    return jsonify({"status": "ignored"}), 200

def run_web_server():
    app.run(host='0.0.0.0', port=8080)

# ===== НАСТРОЙКИ =====
TOKEN = os.environ.get("DISCORD_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
DONATIONALERTS_SECRET = os.environ.get("DONATIONALERTS_SECRET")

if not TOKEN:
    raise ValueError("❌ DISCORD_TOKEN не найден!")
if not GEMINI_API_KEY:
    raise ValueError("❌ GEMINI_API_KEY не найден!")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash')

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

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

def get_user_requests(user_id: str) -> int:
    data = load_data()
    today = datetime.now().strftime("%Y-%m-%d")
    
    if user_id not in data:
        data[user_id] = {"requests": 0, "date": today, "premium_until": None}
    
    if data[user_id].get("date") != today:
        data[user_id]["requests"] = 0
        data[user_id]["date"] = today
    
    save_data(data)
    return data[user_id]["requests"]

def increment_requests(user_id: str) -> int:
    data = load_data()
    today = datetime.now().strftime("%Y-%m-%d")
    
    if user_id not in data:
        data[user_id] = {"requests": 0, "date": today, "premium_until": None}
    
    if data[user_id].get("date") != today:
        data[user_id]["requests"] = 0
        data[user_id]["date"] = today
    
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
    return expire_date > datetime.now()

def add_premium(user_id: str, days: int):
    data = load_data()
    if user_id not in data:
        data[user_id] = {"requests": 0, "date": datetime.now().strftime("%Y-%m-%d"), "premium_until": None}
    
    new_expiry = datetime.now() + timedelta(days=days)
    data[user_id]["premium_until"] = new_expiry.isoformat()
    save_data(data)

def get_remaining_free_requests(user_id: str) -> int:
    used = get_user_requests(user_id)
    return max(0, 4 - used)

# ========== БАЗА УК И ПК ==========
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

# ========== СОБЫТИЕ ГОТОВНОСТИ ==========
@bot.event
async def on_ready():
    print(f"✅ Бот {bot.user} готов!")
    print(f"📜 УК: {len(uk_laws)} статей | ПК: {len(pk_laws)} статей")
    print(f"💎 Система подписки активна (бесплатно: 4 запроса/день, премиум: безлимит)")
    print(f"🔗 DonationAlerts вебхук настроен на /webhook/donationalerts")
    
    try:
        synced = await bot.tree.sync()
        print(f"🔗 Синхронизировано {len(synced)} слэш-команд")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    
    Thread(target=run_web_server, daemon=True).start()
    print("🌐 Веб-сервер запущен на порту 8080")

# ========== ПРЕМИУМ-КОМАНДЫ ==========
@bot.tree.command(name="give_premium", description="[АДМИН] Выдать премиум пользователю")
@app_commands.describe(user="Пользователь", days="Количество дней")
async def give_premium(interaction: discord.Interaction, user: discord.User, days: int):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ У вас нет прав администратора!", ephemeral=True)
        return
    
    add_premium(str(user.id), days)
    embed = discord.Embed(title="✅ Премиум выдан", description=f"{user.mention} получил премиум на **{days}** дней", color=discord.Color.green())
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="premium_status", description="Проверить статус подписки")
async def premium_status(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    premium = is_premium(user_id)
    remaining = get_remaining_free_requests(user_id)
    
    if premium:
        data = load_data()
        expire = data[user_id].get("premium_until", "Неизвестно")
        embed = discord.Embed(title="💎 Премиум статус", description=f"✅ У вас активна премиум-подписка!\n📅 Действует до: {expire[:10]}", color=discord.Color.green())
    else:
        embed = discord.Embed(
            title="💎 Премиум статус",
            description=f"❌ У вас нет активной подписки.\n\n📊 Сегодня осталось: **{remaining}** бесплатных запросов\n💰 Премиум: **60 ₽/месяц** — безлимитные запросы",
            color=discord.Color.orange()
        )
    await interaction.response.send_message(embed=embed, ephemeral=True)

# ========== ОСНОВНЫЕ КОМАНДЫ ==========
@bot.tree.command(name="ук", description="Поиск по Уголовному кодексу")
@app_commands.describe(query="Номер статьи или название")
async def uk_slash(interaction: discord.Interaction, query: str):
    user_id = str(interaction.user.id)
    if not is_premium(user_id):
        remaining = get_remaining_free_requests(user_id)
        if remaining <= 0:
            embed = discord.Embed(
                title="⚠️ Лимит исчерпан",
                description=f"Купите премиум за **60 ₽/месяц**!\n`/купить` — получить ссылку на оплату",
                color=discord.Color.orange()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
    
    await interaction.response.defer()
    results = smart_search(query, uk_laws)
    
    if not results:
        await interaction.followup.send(f"❌ Ничего не найдено по `{query}`")
        return
    
    if not is_premium(user_id):
        increment_requests(user_id)
        remaining = get_remaining_free_requests(user_id)
        await interaction.followup.send(f"📊 Осталось бесплатных запросов сегодня: {remaining}")
    
    if len(results) > 1:
        embed = discord.Embed(title=f"🔍 Найдено {len(results)} статей", color=discord.Color.orange())
        for law in results[:5]:
            section_name = uk_sections.get(law["section"], "Общая часть")
            embed.add_field(name=f"Ст.{law['article']} {law['stars']}", value=f"{law['title']}\n{section_name}", inline=False)
        await interaction.followup.send(embed=embed)
        return
    
    law = results[0]
    section_name = uk_sections.get(law["section"], "Общая часть")
    embed = discord.Embed(title=f"⚖️ Ст {law['article']} УК", description=f"**{law['title']}**\n📌 Раздел: {section_name}\n{law['stars']}", color=discord.Color.red())
    embed.add_field(name="📝 Наказание", value=law['penalty'], inline=False)
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="пк", description="Поиск по Процессуальному кодексу")
@app_commands.describe(query="Номер статьи или тема")
async def pk_slash(interaction: discord.Interaction, query: str):
    user_id = str(interaction.user.id)
    if not is_premium(user_id):
        remaining = get_remaining_free_requests(user_id)
        if remaining <= 0:
            embed = discord.Embed(
                title="⚠️ Лимит исчерпан",
                description=f"Купите премиум за **60 ₽/месяц**!\n`/купить` — получить ссылку на оплату",
                color=discord.Color.orange()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
    
    await interaction.response.defer()
    results = smart_search(query, pk_laws)
    
    if not results:
        await interaction.followup.send(f"❌ Ничего не найдено по `{query}`")
        return
    
    if not is_premium(user_id):
        increment_requests(user_id)
        remaining = get_remaining_free_requests(user_id)
        await interaction.followup.send(f"📊 Осталось бесплатных запросов сегодня: {remaining}")
    
    if len(results) > 1:
        embed = discord.Embed(title=f"🔍 Найдено {len(results)} статей", color=discord.Color.green())
        for law in results[:5]:
            section_name = pk_sections.get(law["section"], "Общая часть")
            embed.add_field(name=f"Ст.{law['article']} {law['stars']}", value=f"{law['title']}\n{section_name}", inline=False)
        await interaction.followup.send(embed=embed)
        return
    
    law = results[0]
    section_name = pk_sections.get(law["section"], "Общая часть")
    embed = discord.Embed(title=f"📜 Ст {law['article']} ПК", description=f"**{law['title']}**\n📌 Раздел: {section_name}\n{law['stars']}", color=discord.Color.green())
    embed.add_field(name="📝 Содержание", value=law['penalty'], inline=False)
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="вопрос", description="Задать вопрос ИИ-адвокату")
@app_commands.describe(question="Ваш вопрос по УК или ПК")
async def ask_question(interaction: discord.Interaction, question: str):
    user_id = str(interaction.user.id)
    if not is_premium(user_id):
        remaining = get_remaining_free_requests(user_id)
        if remaining <= 0:
            embed = discord.Embed(
                title="⚠️ Лимит исчерпан",
                description=f"Купите премиум за **60 ₽/месяц**!\n`/купить` — получить ссылку на оплату",
                color=discord.Color.orange()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
    
    await interaction.response.defer()
    
    if not is_premium(user_id):
        increment_requests(user_id)
        remaining = get_remaining_free_requests(user_id)
        await interaction.followup.send(f"📊 Осталось бесплатных запросов сегодня: {remaining}")
    
    answer = await ask_ai(question)
    embed = discord.Embed(title="⚖️ ИИ-адвокат", description=answer, color=discord.Color.purple())
    await interaction.edit_original_response(content=None, embed=embed)

@bot.tree.command(name="купить", description="Получить ссылку на оплату премиума")
async def buy_premium(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    user_name = interaction.user.name
    
    embed = discord.Embed(
        title="💎 Купить премиум — 60 ₽/месяц",
        description=(
            "🔥 **Что даёт премиум:**\n"
            "• Безлимитные запросы к боту\n"
            "• Приоритетная поддержка\n"
            "• Ранний доступ к новым функциям\n\n"
            "💳 **Как оплатить:**\n"
            "1. Переведите 60 ₽ на карту [ваша карта]\n"
            "2. В комментарии укажите: `!премиум {}`\n"
            "3. После оплаты бот автоматически выдаст вам премиум!\n\n"
            "⚡ Или через DonationAlerts: [ссылка]\n\n"
            "📌 Статус подписки: `/premium_status`"
        ).format(user_id),
        color=discord.Color.gold()
    )
    embed.set_footer(text="Подписка продлевается автоматически каждый месяц")
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="инфо", description="Информация о боте")
async def info_slash(interaction: discord.Interaction):
    embed = discord.Embed(title="📚 Юридический помощник Majestic RP", color=discord.Color.gold())
    embed.add_field(name="💎 Бесплатно", value="• 4 запроса в день на команды `/ук`, `/пк`, `/вопрос`", inline=False)
    embed.add_field(name="💰 Премиум (60 ₽/месяц)", value="• Безлимитные запросы\n• Приоритетная поддержка", inline=False)
    embed.add_field(name="🔗 Команды", value="`/купить` — оплатить премиум\n`/premium_status` — проверить статус\n`/вопрос` — спросить ИИ\n`/ук` и `/пк` — поиск статей\n`/разделы_ук` и `/разделы_пк` — разделы", inline=False)
    await interaction.response.send_message(embed=embed)

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

@bot.tree.command(name="справка", description="Показать все команды")
async def help_slash(interaction: discord.Interaction):
    embed = discord.Embed(title="📚 Помощь", color=discord.Color.gold())
    embed.add_field(name="⚖️ УК", value="`/ук убийство` — поиск", inline=False)
    embed.add_field(name="📜 ПК", value="`/пк задержание` — поиск", inline=False)
    embed.add_field(name="🤖 ИИ", value="`/вопрос Твой вопрос`", inline=False)
    embed.add_field(name="📚 Разделы", value="`/разделы_ук` и `/разделы_пк`", inline=False)
    embed.add_field(name="💎 Премиум", value="`/купить`, `/premium_status`, `/инфо`", inline=False)
    await interaction.response.send_message(embed=embed)

# Префиксные команды
@bot.command(name="вопрос")
async def ask_prefix(ctx, *, question: str):
    user_id = str(ctx.author.id)
    if not is_premium(user_id):
        remaining = get_remaining_free_requests(user_id)
        if remaining <= 0:
            embed = discord.Embed(title="⚠️ Лимит исчерпан", description="Купите премиум за 60 ₽/месяц! `/купить`", color=discord.Color.orange())
            await ctx.send(embed=embed)
            return
    
    async with ctx.typing():
        if not is_premium(user_id):
            increment_requests(user_id)
        answer = await ask_ai(question)
        embed = discord.Embed(title="⚖️ ИИ-адвокат", description=answer, color=discord.Color.blue())
        await ctx.send(embed=embed)

# ЗАПУСК
bot.run(TOKEN)
