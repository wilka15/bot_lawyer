import discord
from discord.ext import commands
from discord import app_commands
import re
import os
from difflib import get_close_matches
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
    raise ValueError("❌ DISCORD_TOKEN не найден!")

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# ========== БАЗА УК ==========
laws = [
    {"article": "6.1", "title": "Умышленное нанесение побоев или иных насильственных действий", "penalty": "от 1 до 3 лет лишения свободы", "stars": "★★★", "note": ""},
    {"article": "6.2", "title": "Убийство (умышленное причинение смерти другому человеку)", "penalty": "от 2 до 4 лет лишения свободы", "stars": "★★★★", "note": ""},
    {"article": "6.3", "title": "Тяжкое убийство", "penalty": "от 4 до 5 лет лишения свободы", "stars": "★★★★★", "note": ""},
    {"article": "6.4", "title": "Угроза убийством или причинением тяжкого вреда здоровью", "penalty": "от 2 до 3 лет лишения свободы, либо штраф $30.000-$50.000", "stars": "★★★", "note": ""},
    {"article": "7.1", "title": "Похищение человека", "penalty": "от 4 до 5 лет лишения свободы", "stars": "★★★★★", "note": ""},
    {"article": "7.4", "title": "Клевета", "penalty": "от 2 до 3 лет лишения свободы либо штраф $40.000-$80.000", "stars": "★★★", "note": ""},
    {"article": "8.1", "title": "Изнасилование", "penalty": "от 3 до 4 лет лишения свободы", "stars": "★★★★", "note": ""},
    {"article": "10.1", "title": "Кража (тайное хищение чужого имущества)", "penalty": "от 2 до 3 лет лишения свободы", "stars": "★★★", "note": ""},
    {"article": "10.2", "title": "Мошенничество", "penalty": "от 2 до 3 лет лишения свободы", "stars": "★★★", "note": ""},
    {"article": "10.3", "title": "Грабеж (открытое хищение чужого имущества)", "penalty": "от 2 до 3 лет лишения свободы", "stars": "★★★", "note": ""},
    {"article": "10.4", "title": "Разбой", "penalty": "от 2 до 4 лет лишения свободы", "stars": "★★★★", "note": ""},
    {"article": "10.5", "title": "Угон транспортного средства", "penalty": "от 1 до 3 лет лишения свободы", "stars": "★★★", "note": ""},
    {"article": "10.9", "title": "Незаконное проникновение в жилище", "penalty": "от 3 до 4 лет лишения свободы", "stars": "★★★★", "note": ""},
    {"article": "11.3", "title": "Уклонение от уплаты налогов", "penalty": "принудительное взыскание в 2-кратном размере + от 3 до 5 лет", "stars": "★★★★★", "note": ""},
    {"article": "12.1", "title": "Терроризм", "penalty": "от 4 до 5 лет лишения свободы", "stars": "★★★★★", "note": ""},
    {"article": "12.8", "title": "Незаконное хранение оружия", "penalty": "от 3 до 4 лет, либо штраф $20.000-$60.000", "stars": "★★★★", "note": ""},
    {"article": "12.14", "title": "Хулиганство", "penalty": "до 2 лет, либо штраф $30.000-$40.000", "stars": "★★", "note": ""},
    {"article": "13.2", "title": "Сбыт наркотиков", "penalty": "от 3 до 5 лет лишения свободы", "stars": "★★★★★", "note": ""},
    {"article": "13.3", "title": "Хранение наркотиков от 5 грамм", "penalty": "от 2 до 4 лет лишения свободы", "stars": "★★★★", "note": ""},
    {"article": "15.4", "title": "Получение взятки", "penalty": "от 4 до 5 лет лишения свободы", "stars": "★★★★★", "note": ""},
    {"article": "15.5", "title": "Дача взятки", "penalty": "от 4 до 5 лет лишения свободы", "stars": "★★★★★", "note": ""},
    {"article": "16.15", "title": "Побег из тюрьмы", "penalty": "от 1 до 5 лет", "stars": "★..★★★★★", "note": ""},
    {"article": "17.1", "title": "Посягательство на жизнь полицейского", "penalty": "от 4 до 5 лет лишения свободы", "stars": "★★★★★", "note": ""},
    {"article": "17.3", "title": "Оскорбление полицейского", "penalty": "от 1 до 3 лет, либо штраф $20.000-$50.000", "stars": "★★★", "note": ""},
    {"article": "19.1", "title": "Браконьерство", "penalty": "от 1 до 3 лет лишения свободы", "stars": "★★★", "note": ""},
]

# ========== БАЗА ПК (в том же формате, что и УК) ==========
# Теперь ПК имеет ТУ ЖЕ СТРУКТУРУ, что и УК для одинакового поиска
pk_laws = [
    {"article": "15", "title": "Задержание (срок до 1 часа)", "penalty": "Задержание на срок до 1 часа", "stars": "⚖️", "note": "ст. 15 ПК"},
    {"article": "16", "title": "Основания задержания", "penalty": "8 оснований: на месте преступления, следы, 3 свидетеля, фото/видео, ордер, требование прокурора, ориентировка, боло-розыск", "stars": "⚖️", "note": "ст. 16 ПК"},
    {"article": "17", "title": "Порядок задержания", "penalty": "11 шагов: наручники → представиться → Миранда → обыск → объяснить причину → доставить в участок → проверить документы → сверить фоторобот → допрос → предложить права → реализовать права", "stars": "⚖️", "note": "ст. 17 ПК"},
    {"article": "19", "title": "Задержание госслужащего", "penalty": "Уведомить руководство и прокуратуру. Если прокурор не приехал за 20 минут — освободить", "stars": "⚖️", "note": "ст. 19 ПК"},
    {"article": "20", "title": "Освобождение подозреваемого", "penalty": "Основания: не подтвердилось, нет лишения свободы, нарушен порядок, прошёл час, неприкосновенность, неуполномоченный сотрудник, незаконные доказательства", "stars": "⚖️", "note": "ст. 20 ПК"},
    {"article": "22", "title": "Права задержанного", "penalty": "Право на адвоката, право хранить молчание, право на ходатайства, право на встречу с адвокатом (10 мин), право на звонок (3 мин)", "stars": "⚖️", "note": "ст. 22 ПК"},
    {"article": "28", "title": "Личный обыск", "penalty": "Только при задержании или аресте. Первичный — для оружия/наркотиков. Вторичный — при аресте, изымается всё", "stars": "⚖️", "note": "ст. 28 ПК"},
    {"article": "29", "title": "Обыск ТС", "penalty": "Обыск — только с ордером CS. Осмотр — при ориентировке или подозрении", "stars": "⚖️", "note": "ст. 29 ПК"},
    {"article": "31", "title": "Видеофиксация", "penalty": "Сотрудник ОБЯЗАН вести видеозапись. Можно приостановить на время вызова адвоката. Хранение 48 часов", "stars": "⚖️", "note": "ст. 31-32 ПК"},
    {"article": "33", "title": "Залог", "penalty": "Минимум $25.000 + $25.000 за каждый уровень розыска", "stars": "💰", "note": "ст. 33 ПК"},
    {"article": "36", "title": "Стадии применения силы", "penalty": "1️⃣ Присутствие 2️⃣ Приказ 3️⃣ Физ. сила 4️⃣ Спецсредства 5️⃣ Огнестрельное оружие", "stars": "💪", "note": "ст. 36 ПК"},
    {"article": "9", "title": "Обжалование", "penalty": "48 часов на обжалование. Жалоба руководителю, в прокуратуру или суд", "stars": "📋", "note": "ст. 9, 43-44 ПК"},
    {"article": "12", "title": "Недопустимые доказательства", "penalty": "Показания ДО прав, слухи, улики добытые незаконно", "stars": "🚫", "note": "ст. 12 ПК"},
    {"article": "56", "title": "Адвокат на допросе", "penalty": "Присутствует, может требовать 5-минутный перерыв, вправе заявлять о нарушениях", "stars": "👨‍⚖️", "note": "ст. 56 ПК"},
    {"article": "М7", "title": "Правило Миранды", "penalty": "«Вы имеете право хранить молчание. Всё, что скажете, может быть использовано против вас. Вы имеете право на адвоката»", "stars": "📢", "note": "Обязательно зачитать при задержании"},
]

# ========== УНИВЕРСАЛЬНЫЙ УМНЫЙ ПОИСК (для УК и ПК) ==========
def smart_search(query: str, database: list, search_type: str = "uk"):
    """
    Универсальный умный поиск для любого кодекса
    database: список статей с полями article, title, penalty, stars, note
    """
    query_lower = query.lower().strip()
    found = []
    
    # 1. Поиск по номеру статьи (как 6.2 или 17)
    match_num = re.search(r'(\d{1,2}(?:\.\d{1,2})?)', query_lower)
    if match_num:
        art_num = match_num.group(1)
        for law in database:
            if law["article"] == art_num:
                return [law]
    
    # 2. Поиск по ключевым словам (с группировкой похожих статей)
    if search_type == "uk":
        keywords_map = {
            "убийств": ["6.2", "6.3"], "побо": ["6.1"], "угроз": ["6.4"],
            "краж": ["10.1"], "грабеж": ["10.3"], "разбо": ["10.4"],
            "угон": ["10.5"], "оружи": ["12.8"], "наркотик": ["13.2", "13.3"],
            "взятк": ["15.4", "15.5"], "побег": ["16.15"], "клевет": ["7.4"],
            "похищ": ["7.1"], "изнасилова": ["8.1"], "хулиган": ["12.14"],
            "браконьер": ["19.1"], "налог": ["11.3"]
        }
    else:  # search_type == "pk"
        keywords_map = {
            "прав": ["22"], "задержан": ["22", "16", "17", "15"], "арест": ["17", "16"],
            "обыск": ["28", "29"], "досмотр": ["28"], "осмотр": ["29"],
            "освобожден": ["20"], "отпуст": ["20"], "обжалован": ["9"], "жалоб": ["9"],
            "залог": ["33"], "деньг": ["33"], "миранд": ["М7"], "сил": ["36"],
            "оружие": ["36"], "стрельб": ["36"], "адвокат": ["56"], "защитник": ["56"],
            "допрос": ["56"], "видео": ["31"], "запис": ["31"], "фиксац": ["31"],
            "госслужащ": ["19"], "полицейск": ["19"], "доказательств": ["12"],
            "улик": ["12"], "срок": ["15"], "время": ["15"], "час": ["15"]
        }
    
    for word, articles in keywords_map.items():
        if word in query_lower:
            for art in articles:
                for law in database:
                    if law["article"] == art and law not in found:
                        found.append(law)
            if found:
                return found
    
    # 3. Поиск по названию
    for law in database:
        if law["title"].lower() in query_lower or query_lower in law["title"].lower():
            if law not in found:
                found.append(law)
    
    # 4. Поиск по примечанию (note) — полезно для ПК
    for law in database:
        if law["note"].lower() in query_lower or query_lower in law["note"].lower():
            if law not in found:
                found.append(law)
    
    # 5. Исправление опечаток (как в УК)
    if not found:
        all_searchable = []
        for law in database:
            all_searchable.append(law["title"].lower())
            all_searchable.append(law["article"].lower())
            all_searchable.append(law["note"].lower())
        
        matches = get_close_matches(query_lower, all_searchable, n=3, cutoff=0.6)
        
        for match in matches:
            for law in database:
                if (match == law["title"].lower() or 
                    match == law["article"].lower() or 
                    match == law["note"].lower()):
                    if law not in found:
                        found.append(law)
    
    return found

# ========== СОБЫТИЕ ГОТОВНОСТИ ==========
@bot.event
async def on_ready():
    print(f"✅ Бот {bot.user} готов помогать адвокатам Majestic RP")
    print(f"📜 Загружено статей УК: {len(laws)}")
    print(f"📚 Загружено статей ПК: {len(pk_laws)}")
    
    try:
        synced = await bot.tree.sync()
        print(f"🔗 Синхронизировано {len(synced)} слэш-команд")
    except Exception as e:
        print(f"❌ Ошибка синхронизации: {e}")
    
    Thread(target=run_web_server, daemon=True).start()
    print("🌐 Веб-сервер запущен на порту 8080")

# ========== ПРЕФИКСНЫЕ КОМАНДЫ (!) ==========
@bot.command(name="ст", aliases=["ук", "статья"])
async def uk_prefix(ctx, *, query: str):
    """!ст 6.2 или !ук убийство"""
    results = smart_search(query, laws, "uk")
    
    if not results:
        await ctx.send(f"❌ Ничего не найдено по запросу `{query}`.\nПопробуйте `!справка`")
        return
    
    if len(results) > 1:
        embed = discord.Embed(title=f"🔍 Найдено {len(results)} статей УК", color=discord.Color.orange())
        for law in results[:5]:
            embed.add_field(name=f"**{law['article']}** {law['stars']}", value=law['title'][:60], inline=False)
        if len(results) > 5:
            embed.set_footer(text=f"И ещё {len(results)-5} статей... уточните запрос")
        await ctx.send(embed=embed)
        return
    
    law = results[0]
    embed = discord.Embed(
        title=f"⚖️ Статья {law['article']} УК SA",
        description=f"**{law['title']}**\n{law['stars']}",
        color=discord.Color.red()
    )
    embed.add_field(name="📝 Наказание", value=law['penalty'], inline=False)
    if law['note']:
        embed.add_field(name="📌 Примечание", value=law['note'], inline=False)
    await ctx.send(embed=embed)

@bot.command(name="пк", aliases=["процесс"])
async def pk_prefix(ctx, *, query: str):
    """!пк задержание — умный поиск по ПК (работает как УК)"""
    results = smart_search(query, pk_laws, "pk")
    
    if not results:
        await ctx.send(f"❌ Ничего не найдено по запросу `{query}`.\nДоступные темы ПК: права, задержание, обыск, освобождение, обжалование, залог, миранда, адвокат, видео, госслужащий, сила, доказательства, срок")
        return
    
    if len(results) > 1:
        embed = discord.Embed(title=f"🔍 Найдено {len(results)} статей ПК", color=discord.Color.green())
        for law in results[:5]:
            embed.add_field(name=f"**Ст. {law['article']}** {law['stars']}", value=law['title'][:60], inline=False)
        if len(results) > 5:
            embed.set_footer(text=f"И ещё {len(results)-5} статей... уточните запрос")
        await ctx.send(embed=embed)
        return
    
    law = results[0]
    embed = discord.Embed(
        title=f"📜 Статья {law['article']} ПК SA",
        description=f"**{law['title']}**\n{law['stars']}",
        color=discord.Color.green()
    )
    embed.add_field(name="📝 Содержание", value=law['penalty'], inline=False)
    if law['note']:
        embed.add_field(name="📌 Источник", value=law['note'], inline=False)
    await ctx.send(embed=embed)

# Быстрые префиксные команды ПК
@bot.command(name="права")
async def rights_prefix(ctx):
    await pk_prefix(ctx, query="права")

@bot.command(name="задержание")
async def arrest_prefix(ctx):
    await pk_prefix(ctx, query="задержание")

@bot.command(name="обыск")
async def search_prefix(ctx):
    await pk_prefix(ctx, query="обыск")

@bot.command(name="освобождение")
async def release_prefix(ctx):
    await pk_prefix(ctx, query="освобождение")

@bot.command(name="обжалование")
async def appeal_prefix(ctx):
    await pk_prefix(ctx, query="обжалование")

@bot.command(name="залог")
async def bail_prefix(ctx):
    await pk_prefix(ctx, query="залог")

@bot.command(name="миранда")
async def miranda_prefix(ctx):
    await pk_prefix(ctx, query="миранда")

@bot.command(name="адвокат")
async def lawyer_prefix(ctx):
    await pk_prefix(ctx, query="адвокат")

@bot.command(name="видео")
async def video_prefix(ctx):
    await pk_prefix(ctx, query="видео")

@bot.command(name="госслужащий")
async def gov_prefix(ctx):
    await pk_prefix(ctx, query="госслужащий")

@bot.command(name="сила")
async def force_prefix(ctx):
    await pk_prefix(ctx, query="сила")

@bot.command(name="доказательства")
async def evidence_prefix(ctx):
    await pk_prefix(ctx, query="доказательства")

@bot.command(name="справка")
async def help_prefix(ctx):
    await help_slash(ctx)

# ========== СЛЭШ-КОМАНДЫ (/) ==========
@bot.tree.command(name="ук", description="Поиск статьи по Уголовному кодексу")
@app_commands.describe(query="Номер статьи (6.2) или название преступления (убийство)")
async def uk_slash(interaction: discord.Interaction, query: str):
    await interaction.response.defer()
    results = smart_search(query, laws, "uk")
    
    if not results:
        await interaction.followup.send(f"❌ Ничего не найдено по запросу `{query}`")
        return
    
    if len(results) > 1:
        embed = discord.Embed(title=f"🔍 Найдено {len(results)} статей УК", color=discord.Color.orange())
        for law in results[:5]:
            embed.add_field(name=f"**{law['article']}** {law['stars']}", value=law['title'][:60], inline=False)
        await interaction.followup.send(embed=embed)
        return
    
    law = results[0]
    embed = discord.Embed(
        title=f"⚖️ Статья {law['article']} УК SA",
        description=f"**{law['title']}**\n{law['stars']}",
        color=discord.Color.red()
    )
    embed.add_field(name="📝 Наказание", value=law['penalty'], inline=False)
    if law['note']:
        embed.add_field(name="📌 Примечание", value=law['note'], inline=False)
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="пк", description="Умный поиск по Процессуальному кодексу (работает как УК)")
@app_commands.describe(query="Номер статьи (17) или тема (задержание, права, обыск)")
async def pk_slash(interaction: discord.Interaction, query: str):
    await interaction.response.defer()
    results = smart_search(query, pk_laws, "pk")
    
    if not results:
        await interaction.followup.send(f"❌ Ничего не найдено по запросу `{query}`\nПримеры: `/пк задержание`, `/пк права`, `/пк 17`")
        return
    
    if len(results) > 1:
        embed = discord.Embed(title=f"🔍 Найдено {len(results)} статей ПК", color=discord.Color.green())
        for law in results[:5]:
            embed.add_field(name=f"**Ст. {law['article']}** {law['stars']}", value=law['title'][:60], inline=False)
        await interaction.followup.send(embed=embed)
        return
    
    law = results[0]
    embed = discord.Embed(
        title=f"📜 Статья {law['article']} ПК SA",
        description=f"**{law['title']}**\n{law['stars']}",
        color=discord.Color.green()
    )
    embed.add_field(name="📝 Содержание", value=law['penalty'], inline=False)
    if law['note']:
        embed.add_field(name="📌 Источник", value=law['note'], inline=False)
    await interaction.followup.send(embed=embed)

# Отдельные слэш-команды для быстрого доступа
@bot.tree.command(name="права", description="Права задержанного (ст. 22 ПК)")
async def rights_slash(interaction: discord.Interaction):
    await interaction.response.defer()
    results = smart_search("права", pk_laws, "pk")
    if results:
        law = results[0]
        embed = discord.Embed(title=f"📜 Ст. {law['article']} ПК", description=f"**{law['title']}**\n{law['stars']}", color=discord.Color.green())
        embed.add_field(name="📝 Содержание", value=law['penalty'], inline=False)
        await interaction.followup.send(embed=embed)

@bot.tree.command(name="задержание", description="Порядок задержания (ст. 17 ПК)")
async def arrest_slash(interaction: discord.Interaction):
    await interaction.response.defer()
    results = smart_search("задержание", pk_laws, "pk")
    if results:
        law = results[0]
        embed = discord.Embed(title=f"📜 Ст. {law['article']} ПК", description=f"**{law['title']}**\n{law['stars']}", color=discord.Color.green())
        embed.add_field(name="📝 Содержание", value=law['penalty'], inline=False)
        await interaction.followup.send(embed=embed)

@bot.tree.command(name="справка", description="Показать список всех команд")
async def help_slash(interaction: discord.Interaction):
    embed = discord.Embed(title="📚 Помощь адвоката Majestic RP", color=discord.Color.gold())
    embed.add_field(name="⚖️ УК", value="`/ук убийство` или `/ук 6.2`\n`!ук убийство` или `!ст 6.2`\n🔹 **Исправляет опечатки!** 🔹", inline=False)
    embed.add_field(name="📜 ПК (ТОЧНО КАК УК)", value="`/пк задержание` или `/пк 17`\n`/пк права`, `/пк обыск`, `/пк освобождение`\n`/пк обжалование`, `/пк залог`, `/пк миранда`\n`/пк адвокат`, `/пк видео`, `/пк госслужащий`\n`/пк сила`, `/пк доказательства`, `/пк срок`\n🔹 **Работает с опечатками!** 🔹\n🔹 **Можно искать по номеру статьи!** 🔹", inline=False)
    embed.set_footer(text="Бот полностью готов к работе в Majestic RP")
    await interaction.response.send_message(embed=embed)

# ЗАПУСК
bot.run(TOKEN)
