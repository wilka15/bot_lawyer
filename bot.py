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
    raise ValueError("❌ DISCORD_TOKEN не найден! Установи переменную окружения.")

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# ========== БАЗА УК ==========
laws = [
    {"article": "6.1", "title": "Умышленное нанесение побоев или иных насильственных действий", "penalty": "от 1 до 3 лет лишения свободы", "stars": "★★★", "note": ""},
    {"article": "6.2", "title": "Убийство (умышленное причинение смерти другому человеку)", "penalty": "от 2 до 4 лет лишения свободы", "stars": "★★★★", "note": ""},
    {"article": "6.3", "title": "Тяжкое убийство (двух и более лиц, с особой жестокостью, группой лиц)", "penalty": "от 4 до 5 лет лишения свободы", "stars": "★★★★★", "note": ""},
    {"article": "6.4", "title": "Угроза убийством или причинением тяжкого вреда здоровью", "penalty": "от 2 до 3 лет лишения свободы, либо штраф $30.000-$50.000", "stars": "★★★", "note": ""},
    {"article": "7.1", "title": "Похищение человека", "penalty": "от 4 до 5 лет лишения свободы", "stars": "★★★★★", "note": ""},
    {"article": "7.4", "title": "Клевета в публичном выступлении или СМИ", "penalty": "от 2 до 3 лет лишения свободы либо штраф $40.000-$80.000", "stars": "★★★", "note": ""},
    {"article": "8.1", "title": "Изнасилование", "penalty": "от 3 до 4 лет лишения свободы", "stars": "★★★★", "note": ""},
    {"article": "10.1", "title": "Кража (тайное хищение чужого имущества)", "penalty": "от 2 до 3 лет лишения свободы", "stars": "★★★", "note": ""},
    {"article": "10.2", "title": "Мошенничество (обман или злоупотребление доверием)", "penalty": "от 2 до 3 лет лишения свободы", "stars": "★★★", "note": ""},
    {"article": "10.3", "title": "Грабеж (открытое хищение чужого имущества)", "penalty": "от 2 до 3 лет лишения свободы", "stars": "★★★", "note": ""},
    {"article": "10.4", "title": "Разбой (нападение с насилием, опасным для жизни)", "penalty": "от 2 до 4 лет лишения свободы", "stars": "★★★★", "note": ""},
    {"article": "10.5", "title": "Неправомерное завладение транспортным средством (угон)", "penalty": "от 1 до 3 лет лишения свободы", "stars": "★★★", "note": ""},
    {"article": "10.9", "title": "Незаконное проникновение в жилище", "penalty": "от 3 до 4 лет лишения свободы", "stars": "★★★★", "note": ""},
    {"article": "11.3", "title": "Уклонение от уплаты налогов", "penalty": "принудительное взыскание в 2-кратном размере + от 3 до 5 лет", "stars": "★★★★★", "note": ""},
    {"article": "12.1", "title": "Терроризм (взрыв, поджог, устрашение населения)", "penalty": "от 4 до 5 лет лишения свободы", "stars": "★★★★★", "note": ""},
    {"article": "12.8", "title": "Незаконное хранение оружия, спецсредств, боеприпасов", "penalty": "от 3 до 4 лет, либо штраф $20.000-$60.000", "stars": "★★★★", "note": ""},
    {"article": "12.14", "title": "Хулиганство", "penalty": "до 2 лет, либо штраф $30.000-$40.000", "stars": "★★", "note": ""},
    {"article": "13.2", "title": "Сбыт, распространение наркотиков", "penalty": "от 3 до 5 лет лишения свободы", "stars": "★★★★★", "note": ""},
    {"article": "13.3", "title": "Хранение наркотиков от 5 грамм", "penalty": "от 2 до 4 лет лишения свободы", "stars": "★★★★", "note": ""},
    {"article": "15.4", "title": "Получение взятки", "penalty": "от 4 до 5 лет лишения свободы", "stars": "★★★★★", "note": ""},
    {"article": "15.5", "title": "Дача взятки должностному лицу", "penalty": "от 4 до 5 лет лишения свободы", "stars": "★★★★★", "note": ""},
    {"article": "16.15", "title": "Уклонение от отбывания наказания (побег)", "penalty": "от 1 до 5 лет", "stars": "★..★★★★★", "note": "Добровольная явка — 1/2 наказания"},
    {"article": "17.1", "title": "Посягательство на жизнь сотрудника правоохранительных органов", "penalty": "от 4 до 5 лет лишения свободы", "stars": "★★★★★", "note": ""},
    {"article": "17.3", "title": "Оскорбление представителя власти при исполнении", "penalty": "от 1 до 3 лет, либо штраф $20.000-$50.000", "stars": "★★★", "note": ""},
    {"article": "17.6", "title": "Неповиновение законному требованию", "penalty": "от 2 до 3 лет, либо штраф $20.000-$60.000", "stars": "★★★", "note": ""},
    {"article": "19.1", "title": "Браконьерство", "penalty": "от 1 до 3 лет лишения свободы", "stars": "★★★", "note": ""},
]

# ========== БАЗА ПК (расширенная для поиска) ==========
procedural_rules = [
    {"keyword": "права задержанного", "title": "Права задержанного", "text": """**Права задержанного (ст. 22 ПК)**:
1️⃣ Право на адвоката
2️⃣ Право сохранять молчание
3️⃣ Право возбуждать ходатайства и заявлять отводы
4️⃣ Право на конфиденциальную встречу с адвокатом (до 10 минут)
5️⃣ Право на один телефонный звонок (до 3 минут)""", "tags": ["права", "задержанный", "задержание", "22"]},
    
    {"keyword": "задержание", "title": "Порядок задержания", "text": """**Порядок задержания (ст. 17 ПК)**:
1. Надеть наручники на подозреваемого
2. Представиться согласно ст. 36 ч.3
3. Зачитать правило Миранды
4. Провести первичный обыск (по желанию)
5. Объяснить причину задержания
6. Доставить в полицейский участок, департамент шерифа или штаб-квартиру FIB
7. Досмотреть документы и проверить трудоустройство
8. Сверить фоторобот
9. Произвести следственные действия (допрос, экспертиза)
10. Предложить реализацию прав
11. Реализовать права задержанного

⏰ **Срок задержания** — не более 1 часа (ст. 15 ПК)""", "tags": ["задержание", "арест", "задержать", "17"]},
    
    {"keyword": "обыск", "title": "Виды обыска", "text": """**Виды обыска по ПК (ст. 28-29)**:
🔹 **Личный обыск** — только при задержании или аресте
🔹 **Первичный обыск** — для обнаружения оружия, наркотиков, взрывчатки
🔹 **Вторичный обыск** — при аресте, изымаются ВСЕ нелегальные предметы
🚗 **Обыск транспортного средства** — только при ордере Car Search (CS)
👁️ **Осмотр ТС** — визуальный осмотр при ориентировке или подозрении

⚠️ Запрещено изымать предметы у госслужащих при первичном обыске""", "tags": ["обыск", "досмотр", "осмотр", "личный обыск", "28", "29"]},
    
    {"keyword": "освобождение", "title": "Основания освобождения", "text": """**Основания для освобождения подозреваемого (ст. 20 ПК)**:
✅ Не подтвердилось подозрение в совершении правонарушения
✅ За нарушение не предусмотрено наказание в виде лишения свободы
✅ Задержание произведено с нарушением ст. 16 ПК
✅ Прошло более 1 часа с момента задержания и не избрана мера наказания
✅ Подозреваемый обладает статусом неприкосновенности
✅ Задержание проводит неуполномоченный сотрудник (стажёр, гражданский)
✅ Доказательства получены незаконным путём""", "tags": ["освобождение", "отпустить", "20"]},
    
    {"keyword": "обжалование", "title": "Порядок обжалования", "text": """**Порядок обжалования (ст. 9, 43-44 ПК)**:
📌 **48 часов** с момента задержания или вынесения наказания
📌 Жалоба подаётся:
   → Руководителю ведомства (дисциплинарная ответственность)
   → В Прокуратуру штата (прокурорская проверка)
   → В суд (во время судебного производства)

📌 Решение может быть отменено, сотрудник привлечён к ответственности""", "tags": ["обжалование", "жалоба", "пожаловаться", "9", "43", "44"]},
    
    {"keyword": "залог", "title": "Выход под залог", "text": """**Выход под залог (ст. 33 ПК)**:
💰 Минимальная сумма: **$25.000**
⭐ За каждый уровень розыска + $25.000 (например, 3 звезды = $25.000 + 3×$25.000 = $100.000)

✔️ Залог доступен по статьям, не влекущим судимость (ст. 5.12 УК)""", "tags": ["залог", "выйти под залог", "деньги", "33"]},
    
    {"keyword": "миранда", "title": "Правило Миранды", "text": """**Правило Миранды (ст. 17 ПК)**:
*"Вы имеете право хранить молчание. Всё, что Вы скажете, может быть и будет использовано против вас. Вы имеете право на адвоката. Частного или государственного. Вам ясны Ваши права?"*

⚠️ Если права не зачитаны — показания считаются недопустимыми (ст. 12 ПК)""", "tags": ["миранда", "права", "зачитать права"]},
    
    {"keyword": "адвокат допрос", "title": "Адвокат на допросе", "text": """**Адвокат на допросе (ст. 56 ПК)**:
✅ Адвокат присутствует при допросе и оказывает юридическую помощь
✅ Имеет право один раз потребовать **5-минутный перерыв** для корректировки тактики
✅ По окончании допроса вправе заявлять о нарушениях прав клиента
⏰ Допрос не может длиться более 1 часа и проводиться в ночное время""", "tags": ["адвокат", "защитник", "допрос", "56"]},
    
    {"keyword": "видеофиксация", "title": "Видеофиксация", "text": """**Видеофиксация (ст. 31-32 ПК)**:
📹 Сотрудник ОБЯЗАН вести видеозапись при пресечении правонарушения и при процессуальных действиях
⏸️ Можно приостановить запись:
   → На время реализации права на адвоката
   → На разбирательство с прокурором/руководством (если задержан госслужащий)
🗄️ Срок хранения: **48 часов**
🚫 При подаче жалобы удалять записи ЗАПРЕЩЕНО""", "tags": ["видео", "запись", "фиксация", "камера", "31", "32"]},
    
    {"keyword": "госслужащий задержание", "title": "Задержание госслужащего", "text": """**Задержание государственного служащего (ст. 19 ПК)**:
👮‍♂️ При задержании госслужащего сотрудник ОБЯЗАН уведомить:
   → Руководство задержанного
   → Прокуратуру штата
⏰ На подтверждение — 10 минут. Срок задержания приостанавливается.
🚨 Если прокурор не прибыл в течение 20 минут — задержанный ОСВОБОЖДАЕТСЯ.
⚖️ При отсутствии состава — немедленное освобождение""", "tags": ["госслужащий", "сотрудник", "полицейский", "19"]},
    
    {"keyword": "стадии силы", "title": "Стадии применения силы", "text": """**Стадии применения силы (ст. 36 ПК)**:
1️⃣ **Присутствие** — форма, знаки отличия, рука на кобуре
2️⃣ **Приказ** — устное требование прекратить нарушение
3️⃣ **Физическая сила** — заломы, удержание, дубинки, аэрозоли
4️⃣ **Спецсредства** — наручники, электрошок, резиновые пули
5️⃣ **Огнестрельное оружие** — только при угрозе жизни (предупредительные выстрелы ЗАПРЕЩЕНЫ)

⚠️ Стадии соблюдаются строго по порядку, кроме случаев прямой угрозы жизни/здоровью""", "tags": ["сила", "оружие", "применение силы", "стрельба", "36"]},
    
    {"keyword": "недопустимые доказательства", "title": "Недопустимые доказательства", "text": """**Недопустимые доказательства (ст. 12 ПК)**:
❌ Показания, полученные ДО зачитывания прав (даже с видео)
❌ Показания, основанные на догадках, слухах
❌ Улики, добытые незаконно (обыск без ордера, изъятие у неприкосновенных лиц)

Такие доказательства не имеют юридической силы и не могут быть использованы для обвинения""", "tags": ["доказательства", "улики", "недопустимые", "12"]},
    
    {"keyword": "срок задержания", "title": "Срок задержания", "text": """**Срок задержания (ст. 15, 20 ПК)**:
⏱️ Максимальный срок: **1 час**
⏸️ Приостанавливается при:
   → Допросе и экспертизе
   → Вызове адвоката (до 10 минут ожидания)
   → Вызове прокуратуры/руководства (если задержан госслужащий)
   → Обыске имущества
   → Просмотре видеофиксации (до +10-20 минут)

⚠️ Если час прошёл, а наказание не назначено — подозреваемый подлежит ОСВОБОЖДЕНИЮ""", "tags": ["срок", "время", "час", "15", "20"]},
]

# ========== ПОИСК ПО УК ==========
def search_uk(query: str):
    """Умный поиск по УК"""
    query_lower = query.lower().strip()
    found = []
    
    # Поиск по номеру статьи
    match_num = re.search(r'(\d{1,2}\.\d{1,2}(?:\.\d{1})?)', query_lower)
    if match_num:
        art_num = match_num.group(1)
        for law in laws:
            if law["article"] == art_num:
                return [law]
    
    # Поиск по ключевым словам (группировка)
    keywords_map = {
        "убийств": ["6.2", "6.3"],
        "побо": ["6.1"],
        "угроз": ["6.4"],
        "похищ": ["7.1"],
        "клевет": ["7.4"],
        "изнасилова": ["8.1"],
        "краж": ["10.1"],
        "мошенничеств": ["10.2"],
        "вымогательств": ["10.2.1"],
        "грабеж": ["10.3"],
        "разбо": ["10.4"],
        "угон": ["10.5", "10.5.1"],
        "уничтожен": ["10.6", "10.7", "10.8"],
        "проникновен": ["10.9", "12.7", "12.7.1", "12.7.2"],
        "налог": ["11.3", "11.4"],
        "терроризм": ["12.1", "12.1.1"],
        "оруж": ["12.8", "12.8.1", "12.8.2", "12.9", "12.10"],
        "наркотик": ["13.1", "13.2", "13.3", "13.4", "13.5"],
        "взятк": ["15.4", "15.5", "15.5.1"],
        "халатность": ["15.6"],
        "ложн": ["16.8", "16.13", "16.13.1", "16.16"],
        "побег": ["16.15"],
        "насили": ["17.1", "17.2"],
        "оскорблен": ["17.3", "17.9"],
        "неповиновен": ["17.6"],
        "браконьерств": ["19.1"],
    }
    
    for word, article_nums in keywords_map.items():
        if word in query_lower:
            for art_num in article_nums:
                for law in laws:
                    if law["article"] == art_num and law not in found:
                        found.append(law)
            if found:
                return found
    
    # Поиск по названию
    for law in laws:
        if law["title"].lower() in query_lower or query_lower in law["title"].lower():
            found.append(law)
    
    # Исправление опечаток
    if not found:
        all_titles = [law["title"].lower() for law in laws]
        matches = get_close_matches(query_lower, all_titles, n=3, cutoff=0.6)
        for match in matches:
            for law in laws:
                if law["title"].lower() == match and law not in found:
                    found.append(law)
    
    return found

# ========== ПОИСК ПО ПК (аналогично УК) ==========
def search_pk(query: str):
    """Умный поиск по ПК"""
    query_lower = query.lower().strip()
    found = []
    
    # Поиск по ключевым словам и тегам
    for rule in procedural_rules:
        # Проверка по ключевому слову
        if rule["keyword"] in query_lower:
            found.append(rule)
            continue
        
        # Проверка по тегам
        for tag in rule["tags"]:
            if tag in query_lower or query_lower in tag:
                if rule not in found:
                    found.append(rule)
                    break
        
        # Проверка по названию
        if rule["title"].lower() in query_lower or query_lower in rule["title"].lower():
            if rule not in found:
                found.append(rule)
    
    # Исправление опечаток
    if not found:
        all_keywords = [rule["keyword"] for rule in procedural_rules]
        all_titles = [rule["title"].lower() for rule in procedural_rules]
        all_tags = [tag for rule in procedural_rules for tag in rule["tags"]]
        
        matches = get_close_matches(query_lower, all_keywords + all_titles + all_tags, n=3, cutoff=0.5)
        
        for match in matches:
            for rule in procedural_rules:
                if (match == rule["keyword"] or 
                    match == rule["title"].lower() or 
                    match in rule["tags"]):
                    if rule not in found:
                        found.append(rule)
    
    return found

# ========== СОБЫТИЕ ГОТОВНОСТИ ==========
@bot.event
async def on_ready():
    print(f"✅ Бот {bot.user} готов помогать адвокатам Majestic RP")
    print(f"📜 Загружено статей УК: {len(laws)}")
    print(f"📚 Загружено тем ПК: {len(procedural_rules)}")
    
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
    results = search_uk(query)
    
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
    embed = discord.Embed(title=f"⚖️ Статья {law['article']} УК SA", description=f"**{law['title']}**\n{law['stars']}", color=discord.Color.red())
    embed.add_field(name="📝 Наказание", value=law['penalty'], inline=False)
    if law['note']:
        embed.add_field(name="📌 Примечание", value=law['note'], inline=False)
    await ctx.send(embed=embed)

@bot.command(name="пк", aliases=["процесс"])
async def pk_prefix(ctx, *, query: str):
    """!пк задержание — умный поиск по ПК"""
    results = search_pk(query)
    
    if not results:
        await ctx.send(f"❌ Ничего не найдено по запросу `{query}`.\nДоступные темы: права, задержание, обыск, освобождение, обжалование, залог, миранда, адвокат, видео, госслужащий, сила, недопустимые доказательства, срок задержания")
        return
    
    if len(results) > 1:
        embed = discord.Embed(title=f"🔍 Найдено {len(results)} тем ПК", color=discord.Color.green())
        for rule in results[:5]:
            embed.add_field(name=f"📌 {rule['title']}", value=f"`!пк {rule['keyword']}` или `/пк {rule['keyword']}`", inline=False)
        await ctx.send(embed=embed)
        return
    
    rule = results[0]
    embed = discord.Embed(title=f"📜 {rule['title']}", description=rule['text'], color=discord.Color.green())
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

@bot.command(name="справка")
async def help_prefix(ctx):
    await help_slash(ctx)

# ========== СЛЭШ-КОМАНДЫ (/) ==========
@bot.tree.command(name="ук", description="Поиск статьи по Уголовному кодексу")
@app_commands.describe(query="Номер статьи (6.2) или название преступления (убийство)")
async def uk_slash(interaction: discord.Interaction, query: str):
    await interaction.response.defer()
    results = search_uk(query)
    
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
    embed = discord.Embed(title=f"⚖️ Статья {law['article']} УК SA", description=f"**{law['title']}**\n{law['stars']}", color=discord.Color.red())
    embed.add_field(name="📝 Наказание", value=law['penalty'], inline=False)
    if law['note']:
        embed.add_field(name="📌 Примечание", value=law['note'], inline=False)
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="пк", description="Умный поиск по Процессуальному кодексу")
@app_commands.describe(query="Тема: права, задержание, обыск, освобождение, обжалование, залог, миранда, адвокат, видео, госслужащий, сила, доказательства, срок")
async def pk_slash(interaction: discord.Interaction, query: str):
    await interaction.response.defer()
    results = search_pk(query)
    
    if not results:
        await interaction.followup.send(f"❌ Ничего не найдено по запросу `{query}`")
        return
    
    if len(results) > 1:
        embed = discord.Embed(title=f"🔍 Найдено {len(results)} тем ПК", color=discord.Color.green())
        for rule in results[:5]:
            embed.add_field(name=f"📌 {rule['title']}", value=f"`/пк {rule['keyword']}`", inline=False)
        await interaction.followup.send(embed=embed)
        return
    
    rule = results[0]
    embed = discord.Embed(title=f"📜 {rule['title']}", description=rule['text'], color=discord.Color.green())
    await interaction.followup.send(embed=embed)

# Отдельные слэш-команды для каждой темы ПК
@bot.tree.command(name="права", description="Права задержанного (ст. 22 ПК)")
async def rights_slash(interaction: discord.Interaction):
    await interaction.response.defer()
    results = search_pk("права")
    if results:
        embed = discord.Embed(title=f"📜 {results[0]['title']}", description=results[0]['text'], color=discord.Color.green())
        await interaction.followup.send(embed=embed)

@bot.tree.command(name="задержание", description="Порядок задержания (ст. 17 ПК)")
async def arrest_slash(interaction: discord.Interaction):
    await interaction.response.defer()
    results = search_pk("задержание")
    if results:
        embed = discord.Embed(title=f"📜 {results[0]['title']}", description=results[0]['text'], color=discord.Color.green())
        await interaction.followup.send(embed=embed)

@bot.tree.command(name="обыск", description="Виды обыска (ст. 28-29 ПК)")
async def search_slash(interaction: discord.Interaction):
    await interaction.response.defer()
    results = search_pk("обыск")
    if results:
        embed = discord.Embed(title=f"📜 {results[0]['title']}", description=results[0]['text'], color=discord.Color.green())
        await interaction.followup.send(embed=embed)

@bot.tree.command(name="освобождение", description="Основания для освобождения (ст. 20 ПК)")
async def release_slash(interaction: discord.Interaction):
    await interaction.response.defer()
    results = search_pk("освобождение")
    if results:
        embed = discord.Embed(title=f"📜 {results[0]['title']}", description=results[0]['text'], color=discord.Color.green())
        await interaction.followup.send(embed=embed)

@bot.tree.command(name="обжалование", description="Порядок обжалования (ст. 9, 43-44 ПК)")
async def appeal_slash(interaction: discord.Interaction):
    await interaction.response.defer()
    results = search_pk("обжалование")
    if results:
        embed = discord.Embed(title=f"📜 {results[0]['title']}", description=results[0]['text'], color=discord.Color.green())
        await interaction.followup.send(embed=embed)

@bot.tree.command(name="залог", description="Выход под залог (ст. 33 ПК)")
async def bail_slash(interaction: discord.Interaction):
    await interaction.response.defer()
    results = search_pk("залог")
    if results:
        embed = discord.Embed(title=f"📜 {results[0]['title']}", description=results[0]['text'], color=discord.Color.green())
        await interaction.followup.send(embed=embed)

@bot.tree.command(name="миранда", description="Правило Миранды")
async def miranda_slash(interaction: discord.Interaction):
    await interaction.response.defer()
    results = search_pk("миранда")
    if results:
        embed = discord.Embed(title=f"📜 {results[0]['title']}", description=results[0]['text'], color=discord.Color.green())
        await interaction.followup.send(embed=embed)

@bot.tree.command(name="адвокат", description="Права адвоката на допросе (ст. 56 ПК)")
async def lawyer_slash(interaction: discord.Interaction):
    await interaction.response.defer()
    results = search_pk("адвокат")
    if results:
        embed = discord.Embed(title=f"📜 {results[0]['title']}", description=results[0]['text'], color=discord.Color.green())
        await interaction.followup.send(embed=embed)

@bot.tree.command(name="видео", description="Видеофиксация (ст. 31-32 ПК)")
async def video_slash(interaction: discord.Interaction):
    await interaction.response.defer()
    results = search_pk("видео")
    if results:
        embed = discord.Embed(title=f"📜 {results[0]['title']}", description=results[0]['text'], color=discord.Color.green())
        await interaction.followup.send(embed=embed)

@bot.tree.command(name="госслужащий", description="Задержание госслужащего (ст. 19 ПК)")
async def gov_slash(interaction: discord.Interaction):
    await interaction.response.defer()
    results = search_pk("госслужащий")
    if results:
        embed = discord.Embed(title=f"📜 {results[0]['title']}", description=results[0]['text'], color=discord.Color.green())
        await interaction.followup.send(embed=embed)

@bot.tree.command(name="сила", description="Стадии применения силы (ст. 36 ПК)")
async def force_slash(interaction: discord.Interaction):
    await interaction.response.defer()
    results = search_pk("сила")
    if results:
        embed = discord.Embed(title=f"📜 {results[0]['title']}", description=results[0]['text'], color=discord.Color.green())
        await interaction.followup.send(embed=embed)

@bot.tree.command(name="справка", description="Показать список всех команд")
async def help_slash(interaction: discord.Interaction):
    embed = discord.Embed(title="📚 Помощь адвоката Majestic RP", color=discord.Color.gold())
    embed.add_field(name="⚖️ УК", value="🔹 `/ук убийство` или `/ук 6.2`\n🔹 `!ук убийство` или `!ст 6.2`\n🔹 Исправляет опечатки и показывает несколько вариантов", inline=False)
    embed.add_field(name="📜 ПК", value="🔹 `/пк задержание` или `!пк задержание`\n🔹 `/права`, `/задержание`, `/обыск`, `/освобождение`\n🔹 `/обжалование`, `/залог`, `/миранда`, `/адвокат`\n🔹 `/видео`, `/госслужащий`, `/сила`\n🔹 Работает так же умно, как и УК!", inline=False)
    await interaction.response.send_message(embed=embed)

# ЗАПУСК
bot.run(TOKEN)
