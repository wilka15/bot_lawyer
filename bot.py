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

# ========== БАЗА УК С РАЗДЕЛАМИ ==========
uk_sections = {
    "VI": "Преступления против жизни и здоровья",
    "VII": "Преступления против свободы, чести и достоинства личности",
    "VIII": "Преступления против половой неприкосновенности",
    "IX": "Преступления против конституционных прав",
    "X": "Преступления против собственности",
    "XI": "Преступления в сфере экономической деятельности",
    "XII": "Преступления против общественной безопасности",
    "XIII": "Преступления в сфере оборота наркотиков",
    "XIV": "Преступления против конституционного строя",
    "XV": "Преступления против власти",
    "XVI": "Преступления против правосудия",
    "XVII": "Преступления против управления",
    "XVIII": "Преступления против военной службы",
    "XIX": "Преступления против окружающей среды",
}

uk_laws = [
    # Глава VI — Преступления против жизни и здоровья
    {"article": "6.1", "section": "VI", "title": "Умышленное нанесение побоев", "penalty": "от 1 до 3 лет лишения свободы", "stars": "★★★", "note": ""},
    {"article": "6.2", "section": "VI", "title": "Убийство", "penalty": "от 2 до 4 лет лишения свободы", "stars": "★★★★", "note": ""},
    {"article": "6.3", "section": "VI", "title": "Тяжкое убийство", "penalty": "от 4 до 5 лет лишения свободы", "stars": "★★★★★", "note": ""},
    {"article": "6.4", "section": "VI", "title": "Угроза убийством", "penalty": "от 2 до 3 лет, либо штраф $30.000-$50.000", "stars": "★★★", "note": ""},
    
    # Глава VII — Преступления против свободы, чести и достоинства
    {"article": "7.1", "section": "VII", "title": "Похищение человека", "penalty": "от 4 до 5 лет лишения свободы", "stars": "★★★★★", "note": ""},
    {"article": "7.4", "section": "VII", "title": "Клевета", "penalty": "от 2 до 3 лет либо штраф $40.000-$80.000", "stars": "★★★", "note": ""},
    
    # Глава VIII — Половые преступления
    {"article": "8.1", "section": "VIII", "title": "Изнасилование", "penalty": "от 3 до 4 лет лишения свободы", "stars": "★★★★", "note": ""},
    
    # Глава X — Преступления против собственности
    {"article": "10.1", "section": "X", "title": "Кража", "penalty": "от 2 до 3 лет лишения свободы", "stars": "★★★", "note": ""},
    {"article": "10.2", "section": "X", "title": "Мошенничество", "penalty": "от 2 до 3 лет лишения свободы", "stars": "★★★", "note": ""},
    {"article": "10.3", "section": "X", "title": "Грабеж", "penalty": "от 2 до 3 лет лишения свободы", "stars": "★★★", "note": ""},
    {"article": "10.4", "section": "X", "title": "Разбой", "penalty": "от 2 до 4 лет лишения свободы", "stars": "★★★★", "note": ""},
    {"article": "10.5", "section": "X", "title": "Угон авто", "penalty": "от 1 до 3 лет лишения свободы", "stars": "★★★", "note": ""},
    {"article": "10.9", "section": "X", "title": "Проникновение в жилище", "penalty": "от 3 до 4 лет лишения свободы", "stars": "★★★★", "note": ""},
    
    # Глава XI — Экономические преступления
    {"article": "11.3", "section": "XI", "title": "Уклонение от налогов", "penalty": "взыскание ×2 + от 3 до 5 лет", "stars": "★★★★★", "note": ""},
    
    # Глава XII — Общественная безопасность
    {"article": "12.1", "section": "XII", "title": "Терроризм", "penalty": "от 4 до 5 лет лишения свободы", "stars": "★★★★★", "note": ""},
    {"article": "12.8", "section": "XII", "title": "Незаконное хранение оружия", "penalty": "от 3 до 4 лет, либо штраф $20.000-$60.000", "stars": "★★★★", "note": ""},
    {"article": "12.14", "section": "XII", "title": "Хулиганство", "penalty": "до 2 лет, либо штраф $30.000-$40.000", "stars": "★★", "note": ""},
    
    # Глава XIII — Наркотики
    {"article": "13.2", "section": "XIII", "title": "Сбыт наркотиков", "penalty": "от 3 до 5 лет лишения свободы", "stars": "★★★★★", "note": ""},
    {"article": "13.3", "section": "XIII", "title": "Хранение наркотиков", "penalty": "от 2 до 4 лет лишения свободы", "stars": "★★★★", "note": ""},
    
    # Глава XV — Преступления против власти
    {"article": "15.4", "section": "XV", "title": "Получение взятки", "penalty": "от 4 до 5 лет лишения свободы", "stars": "★★★★★", "note": ""},
    {"article": "15.5", "section": "XV", "title": "Дача взятки", "penalty": "от 4 до 5 лет лишения свободы", "stars": "★★★★★", "note": ""},
    {"article": "15.7", "section": "XV", "title": "Деструктивное поведение госслужащего", "penalty": "штраф $30.000-$70.000 или до 3 лет", "stars": "★★★", "note": "Унижение, агрессия, нарушение этики"},
    
    # Глава XVI — Правосудие
    {"article": "16.15", "section": "XVI", "title": "Побег из тюрьмы", "penalty": "от 1 до 5 лет", "stars": "★..★★★★★", "note": ""},
    
    # Глава XVII — Управление
    {"article": "17.1", "section": "XVII", "title": "Посягательство на жизнь полицейского", "penalty": "от 4 до 5 лет", "stars": "★★★★★", "note": ""},
    {"article": "17.3", "section": "XVII", "title": "Оскорбление полицейского", "penalty": "штраф $20.000-$50.000 или до 3 лет", "stars": "★★★", "note": "Унижение чести и достоинства"},
    {"article": "17.9", "section": "XVII", "title": "Грубое оскорбление человека", "penalty": "до 2 лет лишения свободы", "stars": "★★", "note": "Унижение в общественном месте"},
    
    # Глава XIX — Окружающая среда
    {"article": "19.1", "section": "XIX", "title": "Браконьерство", "penalty": "от 1 до 3 лет", "stars": "★★★", "note": ""},
]

# ========== БАЗА ПК С РАЗДЕЛАМИ ==========
pk_sections = {
    "I": "Основные положения (ст. 1-14)",
    "II": "Доказательства и доказывание (ст. 11-14)",
    "III": "Меры процессуального принуждения (ст. 15-30)",
    "IV": "Иные положения (ст. 31-39)",
    "V": "Ходатайства и жалобы (ст. 40-44)",
    "VI": "Следствие (ст. 45-64)",
    "VII": "Уголовное производство (ст. 65-77)",
    "VIII": "Терминология (ст. 78)",
}

pk_laws = [
    {"article": "3", "section": "I", "title": "Уважение чести и достоинства", "penalty": "Запрещены унижение, пытки, жестокое обращение", "stars": "⚖️", "note": "ст. 3 ПК"},
    {"article": "15", "section": "III", "title": "Срок задержания", "penalty": "Максимум 1 час", "stars": "⏰", "note": "ст. 15 ПК"},
    {"article": "16", "section": "III", "title": "Основания задержания", "penalty": "8 оснований", "stars": "🔍", "note": "ст. 16 ПК"},
    {"article": "17", "section": "III", "title": "Порядок задержания", "penalty": "11 шагов", "stars": "📋", "note": "ст. 17 ПК"},
    {"article": "19", "section": "III", "title": "Задержание госслужащего", "penalty": "Уведомить руководство и прокуратуру", "stars": "👮", "note": "ст. 19 ПК"},
    {"article": "20", "section": "III", "title": "Освобождение подозреваемого", "penalty": "7 оснований", "stars": "🔓", "note": "ст. 20 ПК"},
    {"article": "22", "section": "III", "title": "Права задержанного", "penalty": "5 прав", "stars": "📜", "note": "ст. 22 ПК"},
    {"article": "28", "section": "III", "title": "Личный обыск", "penalty": "Только при задержании", "stars": "🔎", "note": "ст. 28 ПК"},
    {"article": "29", "section": "III", "title": "Обыск транспорта", "penalty": "Обыск с ордером, осмотр без ордера", "stars": "🚗", "note": "ст. 29 ПК"},
    {"article": "31", "section": "IV", "title": "Видеофиксация", "penalty": "Обязательная запись, хранение 48 часов", "stars": "🎥", "note": "ст. 31-32 ПК"},
    {"article": "33", "section": "IV", "title": "Залог", "penalty": "от $25.000 + $25.000 за звезду", "stars": "💰", "note": "ст. 33 ПК"},
    {"article": "36", "section": "IV", "title": "Применение силы", "penalty": "5 стадий", "stars": "💪", "note": "ст. 36 ПК"},
    {"article": "9", "section": "V", "title": "Обжалование", "penalty": "48 часов", "stars": "📋", "note": "ст. 9, 43-44 ПК"},
    {"article": "12", "section": "II", "title": "Недопустимые доказательства", "penalty": "Показания до прав, слухи, незаконные улики", "stars": "🚫", "note": "ст. 12 ПК"},
    {"article": "56", "section": "VI", "title": "Адвокат на допросе", "penalty": "Присутствует, может взять перерыв", "stars": "👨‍⚖️", "note": "ст. 56 ПК"},
    {"article": "М7", "section": "III", "title": "Правило Миранды", "penalty": "Право молчать и на адвоката", "stars": "📢", "note": "Обязательно зачитать"},
]

# ========== ФУНКЦИЯ ДЛЯ ИИ ==========
async def ask_ai(question: str) -> str:
    """Отправляет вопрос в Gemini и возвращает ответ на основе УК и ПК"""
    try:
        # Формируем контекст из кодексов
        uk_context = "\n".join([f"Ст.{l['article']} ({uk_sections.get(l['section'], 'Общая часть')}): {l['title']} — {l['penalty']}" for l in uk_laws[:20]])
        pk_context = "\n".join([f"Ст.{p['article']} ({pk_sections.get(p['section'], 'Общая часть')}): {p['title']} — {p['penalty']}" for p in pk_laws])
        
        prompt = f"""Ты — юридический помощник в игре Majestic RP. Отвечай на вопросы строго по Уголовному кодексу (УК) и Процессуальному кодексу (ПК) штата Сан-Андреас.

Вот выдержки из кодексов для справки:

УК:
{uk_context}

ПК:
{pk_context}

Отвечай кратко (2-4 предложения), по делу, ссылайся на номера статей и разделы. Если точного ответа нет в кодексах — дай обоснованную рекомендацию.

Вопрос: {question}"""
        
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"❌ Ошибка ИИ: {str(e)}"

# ========== УНИВЕРСАЛЬНЫЙ ПОИСК ==========
def smart_search(query: str, database: list, search_type: str = "uk"):
    query_lower = query.lower().strip()
    found = []
    
    # Поиск по номеру статьи
    match_num = re.search(r'(\d{1,2}(?:\.\d{1,2})?)', query_lower)
    if match_num:
        art_num = match_num.group(1)
        for law in database:
            if law["article"] == art_num:
                return [law]
    
    # Поиск по названию и содержанию
    for law in database:
        if (law["title"].lower() in query_lower or query_lower in law["title"].lower() or
            law["penalty"].lower() in query_lower or query_lower in law["penalty"].lower()):
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

# ========== СОБЫТИЕ ГОТОВНОСТИ ==========
@bot.event
async def on_ready():
    print(f"✅ Бот {bot.user} готов помогать адвокатам Majestic RP")
    print(f"📜 Загружено статей УК: {len(uk_laws)} в {len(uk_sections)} разделах")
    print(f"📚 Загружено статей ПК: {len(pk_laws)} в {len(pk_sections)} разделах")
    
    try:
        synced = await bot.tree.sync()
        print(f"🔗 Синхронизировано {len(synced)} слэш-команд")
    except Exception as e:
        print(f"❌ Ошибка синхронизации: {e}")
    
    Thread(target=run_web_server, daemon=True).start()
    print("🌐 Веб-сервер запущен на порту 8080")

# ========== КОМАНДЫ ПОИСКА ПО РАЗДЕЛАМ ==========
@bot.tree.command(name="разделы_ук", description="Показать все разделы Уголовного кодекса")
async def uk_sections_cmd(interaction: discord.Interaction):
    embed = discord.Embed(title="📚 Разделы Уголовного кодекса", color=discord.Color.red())
    for num, name in uk_sections.items():
        count = len([l for l in uk_laws if l["section"] == num])
        embed.add_field(name=f"Глава {num}", value=f"{name}\n└ {count} статей", inline=True)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="раздел_ук", description="Показать статьи из конкретного раздела УК")
@app_commands.describe(section="Номер раздела (VI, VII, X, XII и т.д.)")
async def uk_section_cmd(interaction: discord.Interaction, section: str):
    section_upper = section.upper()
    if section_upper not in uk_sections:
        await interaction.response.send_message(f"❌ Раздел {section} не найден. Используйте `/разделы_ук` для списка")
        return
    
    articles = [l for l in uk_laws if l["section"] == section_upper]
    embed = discord.Embed(title=f"📚 Раздел {section_upper}: {uk_sections[section_upper]}", color=discord.Color.red())
    for law in articles:
        embed.add_field(name=f"Ст.{law['article']} {law['stars']}", value=f"{law['title']}\n{law['penalty'][:50]}...", inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="разделы_пк", description="Показать все разделы Процессуального кодекса")
async def pk_sections_cmd(interaction: discord.Interaction):
    embed = discord.Embed(title="📚 Разделы Процессуального кодекса", color=discord.Color.green())
    for num, name in pk_sections.items():
        count = len([l for l in pk_laws if l["section"] == num])
        embed.add_field(name=f"Раздел {num}", value=f"{name}\n└ {count} статей", inline=True)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="раздел_пк", description="Показать статьи из конкретного раздела ПК")
@app_commands.describe(section="Номер раздела (I, II, III, IV, V, VI, VII, VIII)")
async def pk_section_cmd(interaction: discord.Interaction, section: str):
    section_upper = section.upper()
    if section_upper not in pk_sections:
        await interaction.response.send_message(f"❌ Раздел {section} не найден. Используйте `/разделы_пк` для списка")
        return
    
    articles = [l for l in pk_laws if l["section"] == section_upper]
    embed = discord.Embed(title=f"📚 Раздел {section_upper}: {pk_sections[section_upper]}", color=discord.Color.green())
    for law in articles:
        embed.add_field(name=f"Ст.{law['article']} {law['stars']}", value=f"{law['title']}\n{law['penalty'][:50]}...", inline=False)
    await interaction.response.send_message(embed=embed)

# ========== БЫСТРЫЙ ПОИСК ==========
@bot.tree.command(name="ук", description="Поиск по Уголовному кодексу")
@app_commands.describe(query="Номер статьи или название преступления")
async def uk_slash(interaction: discord.Interaction, query: str):
    await interaction.response.defer()
    results = smart_search(query, uk_laws, "uk")
    if not results:
        await interaction.followup.send(f"❌ Ничего не найдено по `{query}`\nПопробуйте `/вопрос {query}`")
        return
    if len(results) > 1:
        embed = discord.Embed(title=f"🔍 Найдено {len(results)} статей", color=discord.Color.orange())
        for law in results[:5]:
            section_name = uk_sections.get(law["section"], "Общая часть")
            embed.add_field(name=f"Ст.{law['article']} {law['stars']}", value=f"**{law['title']}**\n{section_name}\n{law['penalty'][:60]}", inline=False)
        await interaction.followup.send(embed=embed)
        return
    law = results[0]
    section_name = uk_sections.get(law["section"], "Общая часть")
    embed = discord.Embed(title=f"⚖️ Ст {law['article']} УК", description=f"**{law['title']}**\n📌 Раздел: {section_name}\n{law['stars']}", color=discord.Color.red())
    embed.add_field(name="📝 Наказание", value=law['penalty'], inline=False)
    if law['note']:
        embed.add_field(name="📌 Примечание", value=law['note'], inline=False)
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="пк", description="Поиск по Процессуальному кодексу")
@app_commands.describe(query="Номер статьи или тема (задержание, права, обыск)")
async def pk_slash(interaction: discord.Interaction, query: str):
    await interaction.response.defer()
    results = smart_search(query, pk_laws, "pk")
    if not results:
        await interaction.followup.send(f"❌ Ничего не найдено по `{query}`\nПопробуйте `/вопрос {query}`")
        return
    if len(results) > 1:
        embed = discord.Embed(title=f"🔍 Найдено {len(results)} статей", color=discord.Color.green())
        for law in results[:5]:
            section_name = pk_sections.get(law["section"], "Общая часть")
            embed.add_field(name=f"Ст.{law['article']} {law['stars']}", value=f"**{law['title']}**\n{section_name}\n{law['penalty'][:60]}", inline=False)
        await interaction.followup.send(embed=embed)
        return
    law = results[0]
    section_name = pk_sections.get(law["section"], "Общая часть")
    embed = discord.Embed(title=f"📜 Ст {law['article']} ПК", description=f"**{law['title']}**\n📌 Раздел: {section_name}\n{law['stars']}", color=discord.Color.green())
    embed.add_field(name="📝 Содержание", value=law['penalty'], inline=False)
    if law['note']:
        embed.add_field(name="📌 Источник", value=law['note'], inline=False)
    await interaction.followup.send(embed=embed)

# ========== ИИ-КОМАНДА ДЛЯ КОНСУЛЬТАЦИЙ ==========
@bot.tree.command(name="вопрос", description="Задать любой вопрос по УК или ПК (ИИ-консультация)")
@app_commands.describe(question="Ваш вопрос по Уголовному или Процессуальному кодексу")
async def ask_question(interaction: discord.Interaction, question: str):
    """/вопрос Какое наказание за кражу? или /вопрос Что делать при обыске?"""
    await interaction.response.defer()
    
    # Сначала пробуем найти в базах
    uk_results = smart_search(question, uk_laws, "uk")
    pk_results = smart_search(question, pk_laws, "pk")
    
    if uk_results or pk_results:
        embed = discord.Embed(title="📚 Найдено в кодексах", description="Возможно, вы искали:", color=discord.Color.blue())
        for law in uk_results[:2]:
            section_name = uk_sections.get(law["section"], "Общая часть")
            embed.add_field(name=f"⚖️ УК Ст.{law['article']}", value=f"**{law['title']}**\n{section_name}\n{law['penalty']}", inline=False)
        for law in pk_results[:2]:
            section_name = pk_sections.get(law["section"], "Общая часть")
            embed.add_field(name=f"📜 ПК Ст.{law['article']}", value=f"**{law['title']}**\n{section_name}\n{law['penalty']}", inline=False)
        embed.set_footer(text="Если это не то, что вы искали — ИИ ответит через момент")
        await interaction.followup.send(embed=embed)
    
    # Отправляем запрос в ИИ
    thinking = await interaction.followup.send("🤖 **ИИ-адвокат анализирует законодательство...**")
    
    answer = await ask_ai(question)
    embed = discord.Embed(title="⚖️ Ответ ИИ-адвоката", description=answer, color=discord.Color.purple())
    await interaction.edit_original_response(content=None, embed=embed)

# ========== КОМАНДА СПРАВКИ ==========
@bot.tree.command(name="справка", description="Показать все команды бота")
async def help_slash(interaction: discord.Interaction):
    embed = discord.Embed(title="📚 Помощь адвоката Majestic RP", color=discord.Color.gold())
    embed.add_field(name="🤖 ИИ-консультация", value="`/вопрос Какое наказание за грабеж?`\n`/вопрос Что делать при обыске?`\n🔹 **ИИ ответит на ЛЮБОЙ вопрос по УК и ПК!** 🔹", inline=False)
    embed.add_field(name="📚 Поиск по разделам", value="`/разделы_ук` — все разделы УК\n`/раздел_ук VI` — статьи раздела VI\n`/разделы_пк` — все разделы ПК\n`/раздел_пк III` — статьи раздела III", inline=False)
    embed.add_field(name="⚖️ Быстрый поиск", value="`/ук убийство` — поиск по УК\n`/пк задержание` — поиск по ПК", inline=False)
    embed.set_footer(text="Бот работает на основе УК и ПК штата Сан-Андреас + ИИ Gemini")
    await interaction.response.send_message(embed=embed)

# Префиксные команды для обратной совместимости
@bot.command(name="вопрос")
async def ask_prefix(ctx, *, question: str):
    async with ctx.typing():
        answer = await ask_ai(question)
        embed = discord.Embed(title="⚖️ ИИ-адвокат", description=answer, color=discord.Color.blue())
        await ctx.send(embed=embed)

# ЗАПУСК
bot.run(TOKEN)
