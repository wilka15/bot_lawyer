import discord
from discord.ext import commands
import re
import google.generativeai as genai
import os
from threading import Thread
from flask import Flask

# ===== ВЕБ-СЕРВЕР ДЛЯ RENDER =====
app = Flask(__name__)

@app.route('/')
def health_check():
    return "✅ Bot is alive!", 200

def run_web_server():
    app.run(host='0.0.0.0', port=8080)

# ===== НАСТРОЙКИ =====
TOKEN = os.environ.get("DISCORD_TOKEN")
if not TOKEN:
    raise ValueError("❌ DISCORD_TOKEN не найден! Установи переменную окружения.")

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("❌ GEMINI_API_KEY не найден! Установи переменную окружения.")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash')

bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())

# ========== ПОЛНАЯ БАЗА УК ==========
laws = [
    {"article": "6.1", "title": "Умышленное нанесение побоев или иных насильственных действий", "penalty": "от 1 до 3 лет лишения свободы", "stars": "★★★", "note": ""},
    {"article": "6.2", "title": "Убийство (умышленное причинение смерти или тяжкий вред здоровью)", "penalty": "от 2 до 4 лет лишения свободы", "stars": "★★★★", "note": ""},
    {"article": "6.3", "title": "Тяжкое убийство (двух и более лиц, с особой жестокостью, группой лиц)", "penalty": "от 4 до 5 лет лишения свободы", "stars": "★★★★★", "note": ""},
    {"article": "6.4", "title": "Угроза убийством или причинением тяжкого вреда здоровью", "penalty": "от 2 до 3 лет лишения свободы, либо штраф $30.000-$50.000", "stars": "★★★", "note": ""},
    {"article": "7.1", "title": "Похищение человека", "penalty": "от 4 до 5 лет лишения свободы", "stars": "★★★★★", "note": ""},
    {"article": "7.4", "title": "Клевета в публичном выступлении или СМИ", "penalty": "от 2 до 3 лет лишения свободы либо штраф $40.000-$80.000", "stars": "★★★", "note": ""},
    {"article": "8.1", "title": "Изнасилование", "penalty": "от 3 до 4 лет лишения свободы", "stars": "★★★★", "note": ""},
    {"article": "10.1", "title": "Кража (тайное хищение)", "penalty": "от 2 до 3 лет лишения свободы", "stars": "★★★", "note": ""},
    {"article": "10.2", "title": "Мошенничество (обман или злоупотребление доверием)", "penalty": "от 2 до 3 лет лишения свободы", "stars": "★★★", "note": ""},
    {"article": "10.3", "title": "Грабеж (открытое хищение)", "penalty": "от 2 до 3 лет лишения свободы", "stars": "★★★", "note": ""},
    {"article": "10.4", "title": "Разбой (нападение с насилием, опасным для жизни)", "penalty": "от 2 до 4 лет лишения свободы", "stars": "★★★★", "note": ""},
    {"article": "10.5", "title": "Неправомерное завладение транспортом (угон)", "penalty": "от 1 до 3 лет лишения свободы", "stars": "★★★", "note": ""},
    {"article": "10.9", "title": "Незаконное проникновение в жилище", "penalty": "от 3 до 4 лет лишения свободы", "stars": "★★★★", "note": ""},
    {"article": "11.3", "title": "Уклонение от уплаты налогов", "penalty": "принудительное взыскание в 2-кратном размере + от 3 до 5 лет", "stars": "★★★★★", "note": ""},
    {"article": "12.1", "title": "Терроризм (взрыв, поджог, устрашение населения)", "penalty": "от 4 до 5 лет лишения свободы", "stars": "★★★★★", "note": ""},
    {"article": "12.8", "title": "Незаконное хранение оружия, спецсредств, боеприпасов", "penalty": "от 3 до 4 лет, либо штраф $20.000-$60.000", "stars": "★★★★", "note": ""},
    {"article": "12.14", "title": "Хулиганство", "penalty": "до 2 лет, либо штраф $30.000-$40.000", "stars": "★★", "note": ""},
    {"article": "13.2", "title": "Сбыт, распространение наркотиков", "penalty": "от 3 до 5 лет лишения свободы", "stars": "★★★★★", "note": ""},
    {"article": "13.3", "title": "Хранение наркотиков от 5 грамм", "penalty": "от 2 до 4 лет лишения свободы", "stars": "★★★★", "note": ""},
    {"article": "15.4", "title": "Получение взятки", "penalty": "от 4 до 5 лет лишения свободы", "stars": "★★★★★", "note": ""},
    {"article": "15.5", "title": "Дача взятки должностному лицу", "penalty": "от 4 до 5 лет лишения свободы", "stars": "★★★★★", "note": ""},
    {"article": "15.6", "title": "Халатность", "penalty": "от 2 до 5 лет, либо штраф $40.000-$70.000", "stars": "★★★★★", "note": ""},
    {"article": "16.15", "title": "Уклонение от отбывания наказания (побег)", "penalty": "от 1 до 5 лет", "stars": "★..★★★★★", "note": "Добровольная явка — 1/2 наказания"},
    {"article": "17.1", "title": "Посягательство на жизнь сотрудника правоохранительных органов", "penalty": "от 4 до 5 лет лишения свободы", "stars": "★★★★★", "note": ""},
    {"article": "17.3", "title": "Оскорбление представителя власти при исполнении", "penalty": "от 1 до 3 лет, либо штраф $20.000-$50.000", "stars": "★★★", "note": ""},
    {"article": "17.6", "title": "Неповиновение законному требованию", "penalty": "от 2 до 3 лет, либо штраф $20.000-$60.000", "stars": "★★★", "note": ""},
    {"article": "19.1", "title": "Браконьерство", "penalty": "от 1 до 3 лет лишения свободы", "stars": "★★★", "note": ""},
]

# ========== БАЗА ПК ==========
procedural_rules = {
    "права задержанного": """**Права задержанного (ст. 22 ПК)**:
1️⃣ Право на адвоката
2️⃣ Право сохранять молчание
3️⃣ Право возбуждать ходатайства
4️⃣ Право на встречу с адвокатом (до 10 минут)
5️⃣ Право на телефонный звонок (до 3 минут)""",

    "задержание": """**Порядок задержания (ст. 17 ПК)**:
1. Надеть наручники
2. Представиться
3. Зачитать правило Миранды
4. Провести первичный обыск
5. Объяснить причину задержания
6. Доставить в участок
7. Проверить документы
8. Сверить фоторобот
9. Провести допрос
⏰ Срок — не более 1 часа""",

    "обыск": """**Виды обыска по ПК (ст. 28-29)**:
🔹 **Личный обыск** — только при задержании или аресте
🔹 **Первичный обыск** — для обнаружения оружия, наркотиков
🔹 **Вторичный обыск** — при аресте, изымается всё
🚗 **Обыск ТС** — только при ордере Car Search""",

    "освобождение": """**Основания для освобождения (ст. 20 ПК)**:
✅ Не подтвердилось подозрение
✅ За нарушение нет лишения свободы
✅ Нарушен порядок задержания
✅ Прошло более 1 часа
✅ Подозреваемый имеет неприкосновенность""",

    "обжалование": """**Порядок обжалования (ст. 9, 43-44 ПК)**:
📌 **48 часов** с момента задержания
📌 Жалоба подаётся руководителю ведомства, в прокуратуру или суд""",

    "залог": """**Выход под залог (ст. 33 ПК)**:
💰 Минимальная сумма: **$25.000**
⭐ За каждый уровень розыска + $25.000""",

    "миранда": """**Правило Миранды**:
*"Вы имеете право хранить молчание. Всё, что Вы скажете, может быть использовано против вас. Вы имеете право на адвоката. Вам ясны Ваши права?"*""",

    "адвокат допрос": """**Адвокат на допросе (ст. 56 ПК)**:
✅ Присутствует при допросе
✅ Может потребовать 5-минутный перерыв
✅ Вправе заявлять о нарушениях прав клиента""",
}

# ========== ФУНКЦИЯ ПОИСКА ==========
def find_article(query: str):
    query_lower = query.lower().strip()
    
    match_num = re.search(r'(\d{1,2}\.\d{1,2}(?:\.\d{1})?)', query_lower)
    if match_num:
        art_num = match_num.group(1)
        for law in laws:
            if law["article"] == art_num:
                return law
    
    keywords = {
        "убийство": "6.2", "кража": "10.1", "грабеж": "10.3", "разбой": "10.4",
        "угон": "10.5", "оружие": "12.8", "наркотики": "13.2", "взятка": "15.4",
        "побег": "16.15", "хулиганство": "12.14", "клевета": "7.4"
    }
    
    for word, article_num in keywords.items():
        if word in query_lower:
            for law in laws:
                if law["article"] == article_num:
                    return law
    
    for law in laws:
        if law["title"].lower() in query_lower or query_lower in law["title"].lower():
            return law
    
    return None

# ========== КОМАНДЫ ==========
@bot.event
async def on_ready():
    print(f"✅ Бот {bot.user} готов помогать адвокатам Majestic RP")
    print(f"📜 Загружено статей УК: {len(laws)}")
    print(f"📚 Загружено тем ПК: {len(procedural_rules)}")
    Thread(target=run_web_server, daemon=True).start()
    print("🌐 Веб-сервер запущен на порту 8080")

@bot.command(name="ст", aliases=["ук", "статья"])
async def uk_article(ctx, *, query: str):
    """!ст 6.2 или !ук убийство"""
    law = find_article(query)
    if law:
        embed = discord.Embed(
            title=f"⚖️ Статья {law['article']} УК SA",
            description=f"**{law['title']}**\n{law['stars']}",
            color=discord.Color.red()
        )
        embed.add_field(name="📝 Наказание", value=law["penalty"], inline=False)
        if law["note"]:
            embed.add_field(name="📌 Примечание", value=law["note"], inline=False)
        await ctx.send(embed=embed)
    else:
        await ctx.send(f"❌ Статья не найдена: `{query}`\nПример: `!ст 6.2` или `!ук убийство`")

@bot.command(name="пк", aliases=["процесс"])
async def pk_search(ctx, *, query: str):
    """!пк задержание"""
    query_lower = query.lower()
    for keyword, text in procedural_rules.items():
        if keyword in query_lower or query_lower in keyword:
            embed = discord.Embed(
                title=f"📜 {keyword.upper()}",
                description=text,
                color=discord.Color.green()
            )
            await ctx.send(embed=embed)
            return
    topics = ", ".join(procedural_rules.keys())
    await ctx.send(f"❌ Тема не найдена. Доступно: {topics}")

# Быстрые команды ПК
@bot.command(name="права")
async def rights(ctx):
    await pk_search(ctx, query="права задержанного")

@bot.command(name="задержание")
async def arrest_procedure(ctx):
    await pk_search(ctx, query="задержание")

@bot.command(name="обыск")
async def search_procedure(ctx):
    await pk_search(ctx, query="обыск")

@bot.command(name="освобождение")
async def release(ctx):
    await pk_search(ctx, query="освобождение")

@bot.command(name="обжалование")
async def appeal(ctx):
    await pk_search(ctx, query="обжалование")

@bot.command(name="залог")
async def bail(ctx):
    await pk_search(ctx, query="залог")

@bot.command(name="миранда")
async def miranda(ctx):
    await pk_search(ctx, query="миранда")

@bot.command(name="адвокат")
async def lawyer_duty(ctx):
    await pk_search(ctx, query="адвокат допрос")

@bot.command(name="вопрос")
async def ask_ai(ctx, *, question: str):
    """!вопрос Какое наказание за убийство?"""
    async with ctx.typing():
        try:
            prompt = f"""Ты — юридический помощник в игре Majestic RP. 
Отвечай строго по УК и ПК штата Сан-Андреас. Кратко, по делу.

Вопрос: {question}"""
            response = model.generate_content(prompt)
            answer = response.text
        except Exception as e:
            answer = f"❌ Ошибка ИИ: {e}"
    embed = discord.Embed(title="🤖 ИИ-адвокат", description=answer, color=discord.Color.blue())
    await ctx.send(embed=embed)

@bot.command(name="справка")
async def help_bot(ctx):
    embed = discord.Embed(title="📚 Помощь адвоката Majestic RP", color=discord.Color.gold())
    embed.add_field(name="⚖️ УК", value="`!ст 6.2` | `!ук убийство`", inline=False)
    embed.add_field(name="📜 ПК", value="`!права`, `!задержание`, `!обыск`, `!адвокат`, `!миранда`, `!освобождение`, `!обжалование`, `!залог`", inline=False)
    embed.add_field(name="🧠 ИИ", value="`!вопрос Твой вопрос`", inline=False)
    await ctx.send(embed=embed)

# ЗАПУСК
bot.run(TOKEN)
