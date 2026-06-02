import discord
from discord.ext import commands
from discord import app_commands
import re
import os
from difflib import get_close_matches
from threading import Thread
from flask import Flask
import google.generativeai as genai

# ===== ВЕБ-СЕРВЕР ДЛЯ RENDER =====
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
    raise ValueError("❌ DISCORD_TOKEN не найден!")
if not GEMINI_API_KEY:
    raise ValueError("❌ GEMINI_API_KEY не найден!")

# Настройка Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash')

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# ========== БАЗА УК ==========
laws = [
    {"article": "6.1", "title": "Умышленное нанесение побоев", "penalty": "от 1 до 3 лет", "stars": "★★★", "note": ""},
    {"article": "6.2", "title": "Убийство", "penalty": "от 2 до 4 лет", "stars": "★★★★", "note": ""},
    {"article": "6.3", "title": "Тяжкое убийство", "penalty": "от 4 до 5 лет", "stars": "★★★★★", "note": ""},
    {"article": "6.4", "title": "Угроза убийством", "penalty": "от 2 до 3 лет, либо штраф $30.000-$50.000", "stars": "★★★", "note": ""},
    {"article": "7.1", "title": "Похищение человека", "penalty": "от 4 до 5 лет", "stars": "★★★★★", "note": ""},
    {"article": "7.4", "title": "Клевета", "penalty": "от 2 до 3 лет либо штраф $40.000-$80.000", "stars": "★★★", "note": ""},
    {"article": "8.1", "title": "Изнасилование", "penalty": "от 3 до 4 лет", "stars": "★★★★", "note": ""},
    {"article": "10.1", "title": "Кража", "penalty": "от 2 до 3 лет", "stars": "★★★", "note": ""},
    {"article": "10.2", "title": "Мошенничество", "penalty": "от 2 до 3 лет", "stars": "★★★", "note": ""},
    {"article": "10.3", "title": "Грабеж", "penalty": "от 2 до 3 лет", "stars": "★★★", "note": ""},
    {"article": "10.4", "title": "Разбой", "penalty": "от 2 до 4 лет", "stars": "★★★★", "note": ""},
    {"article": "10.5", "title": "Угон авто", "penalty": "от 1 до 3 лет", "stars": "★★★", "note": ""},
    {"article": "10.9", "title": "Проникновение в жилище", "penalty": "от 3 до 4 лет", "stars": "★★★★", "note": ""},
    {"article": "11.3", "title": "Уклонение от налогов", "penalty": "взыскание ×2 + от 3 до 5 лет", "stars": "★★★★★", "note": ""},
    {"article": "12.1", "title": "Терроризм", "penalty": "от 4 до 5 лет", "stars": "★★★★★", "note": ""},
    {"article": "12.8", "title": "Незаконное хранение оружия", "penalty": "от 3 до 4 лет, либо штраф $20.000-$60.000", "stars": "★★★★", "note": ""},
    {"article": "12.14", "title": "Хулиганство", "penalty": "до 2 лет, либо штраф $30.000-$40.000", "stars": "★★", "note": ""},
    {"article": "13.2", "title": "Сбыт наркотиков", "penalty": "от 3 до 5 лет", "stars": "★★★★★", "note": ""},
    {"article": "13.3", "title": "Хранение наркотиков", "penalty": "от 2 до 4 лет", "stars": "★★★★", "note": ""},
    {"article": "15.4", "title": "Получение взятки", "penalty": "от 4 до 5 лет", "stars": "★★★★★", "note": ""},
    {"article": "15.5", "title": "Дача взятки", "penalty": "от 4 до 5 лет", "stars": "★★★★★", "note": ""},
    {"article": "15.7", "title": "Деструктивное поведение госслужащего", "penalty": "штраф $30.000-$70.000 или до 3 лет", "stars": "★★★", "note": "Унижение, агрессия, нарушение этики"},
    {"article": "16.15", "title": "Побег из тюрьмы", "penalty": "от 1 до 5 лет", "stars": "★..★★★★★", "note": ""},
    {"article": "17.1", "title": "Посягательство на жизнь полицейского", "penalty": "от 4 до 5 лет", "stars": "★★★★★", "note": ""},
    {"article": "17.3", "title": "Оскорбление полицейского", "penalty": "штраф $20.000-$50.000 или до 3 лет", "stars": "★★★", "note": "Унижение чести и достоинства"},
    {"article": "17.9", "title": "Грубое оскорбление человека", "penalty": "до 2 лет лишения свободы", "stars": "★★", "note": "Унижение в общественном месте"},
    {"article": "19.1", "title": "Браконьерство", "penalty": "от 1 до 3 лет", "stars": "★★★", "note": ""},
]

# ========== БАЗА ПК ==========
pk_laws = [
    {"article": "3", "title": "Уважение чести и достоинства личности", "penalty": "Запрещены унижение, пытки, жестокое обращение", "stars": "⚖️", "note": "ст. 3 ПК"},
    {"article": "15", "title": "Срок задержания", "penalty": "Максимум 1 час", "stars": "⏰", "note": "ст. 15 ПК"},
    {"article": "16", "title": "Основания задержания", "penalty": "8 оснований", "stars": "🔍", "note": "ст. 16 ПК"},
    {"article": "17", "title": "Порядок задержания", "penalty": "11 шагов", "stars": "📋", "note": "ст. 17 ПК"},
    {"article": "19", "title": "Задержание госслужащего", "penalty": "Уведомить руководство и прокуратуру", "stars": "👮", "note": "ст. 19 ПК"},
    {"article": "20", "title": "Освобождение подозреваемого", "penalty": "7 оснований", "stars": "🔓", "note": "ст. 20 ПК"},
    {"article": "22", "title": "Права задержанного", "penalty": "5 прав", "stars": "📜", "note": "ст. 22 ПК"},
    {"article": "28", "title": "Личный обыск", "penalty": "Только при задержании", "stars": "🔎", "note": "ст. 28 ПК"},
    {"article": "29", "title": "Обыск транспорта", "penalty": "Обыск с ордером, осмотр без ордера", "stars": "🚗", "note": "ст. 29 ПК"},
    {"article": "31", "title": "Видеофиксация", "penalty": "Обязательная запись, хранение 48 часов", "stars": "🎥", "note": "ст. 31-32 ПК"},
    {"article": "33", "title": "Залог", "penalty": "от $25.000 + $25.000 за звезду", "stars": "💰", "note": "ст. 33 ПК"},
    {"article": "36", "title": "Применение силы", "penalty": "5 стадий", "stars": "💪", "note": "ст. 36 ПК"},
    {"article": "9", "title": "Обжалование", "penalty": "48 часов", "stars": "📋", "note": "ст. 9, 43-44 ПК"},
    {"article": "12", "title": "Недопустимые доказательства", "penalty": "Показания до прав, слухи, незаконные улики", "stars": "🚫", "note": "ст. 12 ПК"},
    {"article": "56", "title": "Адвокат на допросе", "penalty": "Присутствует, может взять перерыв", "stars": "👨‍⚖️", "note": "ст. 56 ПК"},
    {"article": "М7", "title": "Правило Миранды", "penalty": "Право молчать и на адвоката", "stars": "📢", "note": "Обязательно зачитать"},
]

# ========== ФУНКЦИЯ ДЛЯ ИИ ==========
async def ask_ai(question: str) -> str:
    """Отправляет вопрос в Gemini и возвращает ответ на основе УК и ПК"""
    try:
        # Формируем контекст из кодексов
        uk_context = "\n".join([f"Ст.{l['article']}: {l['title']} — {l['penalty']}" for l in laws[:15]])
        pk_context = "\n".join([f"Ст.{p['article']}: {p['title']} — {p['penalty']}" for p in pk_laws[:10]])
        
        prompt = f"""Ты — юридический помощник в игре Majestic RP. Отвечай на вопросы строго по Уголовному кодексу и Процессуальному кодексу штата Сан-Андреас.

Вот выдержки из кодексов для справки:

УК:
{uk_context}

ПК:
{pk_context}

Отвечай кратко (2-4 предложения), по делу, ссылайся на номера статей. Если точного ответа нет в кодексах — дай обоснованную рекомендацию.

Вопрос: {question}"""
        
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"❌ Ошибка ИИ: {str(e)}"

# ========== УМНЫЙ ПОИСК ==========
def smart_search(query: str, database: list, search_type: str = "uk"):
    query_lower = query.lower().strip()
    found = []
    
    # Поиск по номеру
    match_num = re.search(r'(\d{1,2}(?:\.\d{1,2})?)', query_lower)
    if match_num:
        art_num = match_num.group(1)
        for law in database:
            if law["article"] == art_num:
                return [law]
    
    # Поиск по ключевым словам
    for law in database:
        if law["title"].lower() in query_lower or query_lower in law["title"].lower():
            found.append(law)
        elif law["penalty"].lower() in query_lower or query_lower in law["penalty"].lower():
            found.append(law)
    
    # Исправление опечаток
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

# ========== СОБЫТИЯ ==========
@bot.event
async def on_ready():
    print(f"✅ Бот {bot.user} готов!")
    print(f"📜 УК: {len(laws)} статей | ПК: {len(pk_laws)} статей")
    
    try:
        synced = await bot.tree.sync()
        print(f"🔗 Синхронизировано {len(synced)} слэш-команд")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    
    Thread(target=run_web_server, daemon=True).start()
    print("🌐 Веб-сервер запущен")

# ========== УНИВЕРСАЛЬНАЯ ИИ-КОМАНДА ==========
@bot.tree.command(name="вопрос", description="Задать любой вопрос по УК или ПК (например: Какое наказание за убийство?)")
@app_commands.describe(question="Ваш вопрос по Уголовному или Процессуальному кодексу")
async def ask_question(interaction: discord.Interaction, question: str):
    """/вопрос Какое наказание за кражу?"""
    await interaction.response.defer()
    
    # Сначала пробуем найти в базах
    uk_results = smart_search(question, laws, "uk")
    pk_results = smart_search(question, pk_laws, "pk")
    
    if uk_results or pk_results:
        # Если нашли в базах — показываем быстрый ответ
        embed = discord.Embed(title="📚 Найдено в кодексах", color=discord.Color.blue())
        for law in uk_results[:2]:
            embed.add_field(name=f"⚖️ УК Ст.{law['article']}", value=f"**{law['title']}**\n{law['penalty']}", inline=False)
        for law in pk_results[:2]:
            embed.add_field(name=f"📜 ПК Ст.{law['article']}", value=f"**{law['title']}**\n{law['penalty']}", inline=False)
        await interaction.followup.send(embed=embed)
    else:
        # Если не нашли — используем ИИ
        embed = discord.Embed(title="🤖 ИИ-адвокат анализирует...", description="Подождите немного", color=discord.Color.purple())
        await interaction.followup.send(embed=embed)
        
        answer = await ask_ai(question)
        embed = discord.Embed(title="⚖️ Ответ ИИ-адвоката", description=answer, color=discord.Color.green())
        await interaction.edit_original_response(embed=embed)

# ========== ОБЫЧНЫЕ КОМАНДЫ ==========
@bot.tree.command(name="ук", description="Поиск по Уголовному кодексу")
@app_commands.describe(query="Номер статьи или название преступления")
async def uk_slash(interaction: discord.Interaction, query: str):
    await interaction.response.defer()
    results = smart_search(query, laws, "uk")
    if not results:
        await interaction.followup.send(f"❌ Ничего не найдено по `{query}`\nПопробуйте `/вопрос {query}`")
        return
    law = results[0]
    embed = discord.Embed(title=f"⚖️ Ст {law['article']} УК", description=f"**{law['title']}**\n{law['stars']}", color=discord.Color.red())
    embed.add_field(name="📝 Наказание", value=law['penalty'], inline=False)
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="пк", description="Поиск по Процессуальному кодексу")
@app_commands.describe(query="Тема: задержание, права, обыск, унижение и т.д.")
async def pk_slash(interaction: discord.Interaction, query: str):
    await interaction.response.defer()
    results = smart_search(query, pk_laws, "pk")
    if not results:
        await interaction.followup.send(f"❌ Ничего не найдено по `{query}`\nПопробуйте `/вопрос {query}`")
        return
    law = results[0]
    embed = discord.Embed(title=f"📜 Ст {law['article']} ПК", description=f"**{law['title']}**\n{law['stars']}", color=discord.Color.green())
    embed.add_field(name="📝 Содержание", value=law['penalty'], inline=False)
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="справка", description="Показать все команды")
async def help_slash(interaction: discord.Interaction):
    embed = discord.Embed(title="📚 Помощь адвоката Majestic RP", color=discord.Color.gold())
    embed.add_field(name="🤖 Универсальный вопрос", value="`/вопрос Какое наказание за грабеж?`\n`/вопрос Что делать при обыске?`\n`/вопрос Как обжаловать штраф?`\n🔹 **ИИ ответит на ЛЮБОЙ вопрос по УК и ПК!** 🔹", inline=False)
    embed.add_field(name="⚖️ Быстрый поиск по УК", value="`/ук убийство` или `/ук 6.2`", inline=False)
    embed.add_field(name="📜 Быстрый поиск по ПК", value="`/пк задержание`, `/пк права`, `/пк унижение`", inline=False)
    embed.set_footer(text="Бот работает на основе УК и ПК штата Сан-Андреас + ИИ Gemini")
    await interaction.response.send_message(embed=embed)

# Префиксные команды (для совместимости)
@bot.command(name="вопрос")
async def ask_prefix(ctx, *, question: str):
    """!вопрос Какое наказание за убийство?"""
    async with ctx.typing():
        answer = await ask_ai(question)
        embed = discord.Embed(title="⚖️ ИИ-адвокат", description=answer, color=discord.Color.blue())
        await ctx.send(embed=embed)

# ЗАПУСК
bot.run(TOKEN)
