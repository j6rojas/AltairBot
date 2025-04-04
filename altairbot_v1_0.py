#pip install discord.py python-dotenv requests

import os
import discord
from discord.ext import commands
import requests
from dotenv import load_dotenv
from difflib import SequenceMatcher
import random
import asyncio

load_dotenv()
TOKEN = "Enter Discord Bot TOKEN here"

if not TOKEN:
    print("Error: DISCORD_BOT_TOKEN is not set. Please check your .env file.")
else:
    print("DISCORD_BOT_TOKEN loaded successfully.")

bot = commands.Bot(command_prefix='!', intents=discord.Intents.all())

EXCLUDED_CATEGORY = "COMPUTER SCIENCE"
ALLOWED_SOURCES = ["Official", "CSUB", "05Nats", "98Nats"]
ALL_CATEGORIES = ["ASTRONOMY", "EARTH AND SPACE", "EARTH SCIENCE", "MATH", "ENERGY", "BIOLOGY", "CHEMISTRY", "PHYSICS", "GENERAL SCIENCE"]
pending_answers = {}  # Now stores: {channel_id: {answer_data, question_type, active, answered_users, source, wrong_teams, phase, bonus_team}}
teams = {}  # Format: {team_name: {"captain": user_id, "members": set(), "points": 0}}
team_members = {}  # Format: {user_id: team_name}
game_active = {}  # Format: {channel_id: bool}
user_streaks = {}  # Format: {user_id: streak_count}

CATEGORY_EMOJIS = {
    "ASTRONOMY": "🔭",
    "EARTH AND SPACE": "🌍",
    "EARTH SCIENCE": "🌍",
    "MATH": "📐",
    "ENERGY": "⚡",
    "BIOLOGY": "🧬",
    "CHEMISTRY": "⚗️",
    "PHYSICS": "🔬",
    "GENERAL SCIENCE": "🔬"
}
CATEGORY_COLORS = {
    "ASTRONOMY": discord.Color.dark_blue(),
    "EARTH AND SPACE": discord.Color.blue(),
    "EARTH SCIENCE": discord.Color.blue(),
    "MATH": discord.Color.green(),
    "ENERGY": discord.Color.orange(),
    "BIOLOGY": discord.Color.green(),
    "CHEMISTRY": discord.Color.purple(),
    "PHYSICS": discord.Color.red(),
    "GENERAL SCIENCE": discord.Color.teal()
}

team_panel_message = None

def parse_answer(answer_text, source):
    answer_text = answer_text.strip().upper()
    source_upper = str(source).upper()

    # Handle all 98Nats variants (case-insensitive)
    if source_upper.startswith("98NATS"):
        if answer_text.startswith("ANSWER: "):
            answer_part = answer_text.split("ANSWER: ", 1)[1]
        else:
            answer_part = answer_text

        mcq_answer = next((c for c in answer_part if c in {'W', 'X', 'Y', 'Z'}), None)
        if mcq_answer:
            return 'mcq', mcq_answer, ''
        return 'short', answer_part, ''

    # Handle acceptable answers in parentheses
    if answer_text.startswith("ANSWER: "):
        answer_part = answer_text.split("ANSWER: ")[1].strip()
        if '(' in answer_part and ')' in answer_part:
            main_answer = answer_part.split('(', 1)[0].strip()
            accept_answer = answer_part.split('(', 1)[1].split(')', 1)[0].replace("ACCEPT:", "").strip()
            return 'short', main_answer, accept_answer
        if '--' in answer_part:
            mcq_answer = answer_part.split('--')[0].strip()
            word_answer = answer_part.split('--')[1].strip()
            return 'mcq', mcq_answer, word_answer
        else:
            parts = answer_part.split(')', 1)
            mcq_answer = parts[0].strip() if len(parts) > 1 else answer_part.split()[0].strip()
            word_answer = parts[1].strip() if len(parts) > 1 else ' '.join(answer_part.split()[1:]).strip()

        if mcq_answer in {'W', 'X', 'Y', 'Z'}:
            return 'mcq', mcq_answer, word_answer

    return 'short', answer_text.split("ANSWER: ")[-1].split(')')[0].strip(), ''

def is_similar(answer1, answer2, threshold=0.8):
    return SequenceMatcher(None, answer1, answer2).ratio() >= threshold

def get_question_by_category(category):
    url = "https://scibowldb.com/api/questions/random"
    if category:
        if isinstance(category, list):
            # Join multiple categories with commas
            url += f"?category={','.join(category)}"
        else:
            url += f"?category={category}"
    return requests.get(url)

@bot.command(name='question', help='Get a random Science Bowl question')
async def science_question(ctx, source: str = None):
    if source and source in ALLOWED_SOURCES:
        await fetch_question(ctx.channel, sources=[source])
    else:
        await fetch_question(ctx.channel, category=[cat for cat in ALL_CATEGORIES if cat != EXCLUDED_CATEGORY])

@bot.command(name='math', help='Get a math Science Bowl question')
async def math_question(ctx):
    await fetch_question(ctx.channel, category=["MATH"])

@bot.command(name='es', help='Get an Earth Science and Earth and Space Science question')
async def es_question(ctx):
    await fetch_question(ctx.channel, category=["EARTH SCIENCE", "EARTH AND SPACE"])

@bot.command(name='gen', help='Get a General Science question')
async def gen_question(ctx):
    await fetch_question(ctx.channel, category=["GENERAL SCIENCE"])

@bot.command(name='chem', help='Get a Chemistry question')
async def chem_question(ctx):
    await fetch_question(ctx.channel, category=["CHEMISTRY"])

@bot.command(name='astro', help='Get an Astronomy question')
async def astro_question(ctx):
    await fetch_question(ctx.channel, category=["ASTRONOMY"])

@bot.command(name='energy', help='Get an Energy question')
async def energy_question(ctx):
    await fetch_question(ctx.channel, category=["ENERGY"])

@bot.command(name='physics', help='Get a Physics question')
async def physics_question(ctx):
    await fetch_question(ctx.channel, category=["PHYSICS"])

@bot.command(name='bio', help='Get a Biology question')
async def bio_question(ctx):
    await fetch_question(ctx.channel, category=["BIOLOGY"])

@bot.command(name='skip', help='Skip the current question')
async def skip_question(ctx):
    if ctx.channel.id in pending_answers:
        data = pending_answers[ctx.channel.id]
        correct_answer = data["answer"]

        await ctx.send(f"❌ Question skipped! Correct answer was: **{correct_answer}**")

        pending_answers[ctx.channel.id]["active"] = False
    else:
        await ctx.send("There is no active question to skip.")

@bot.command(name='create', help='Create a team (max 2 teams)')
async def create_team(ctx, team_name):
    global teams
    team_name = team_name.upper().strip()
    if len(teams) >= 2:
        await ctx.send("Maximum of 2 teams allowed!")
        return
    if team_name in teams:
        await ctx.send("Team name already exists!")
        return
    teams[team_name] = {"captain": ctx.author.id, "members": set([ctx.author.id]), "points": 0}
    team_members[ctx.author.id] = team_name
    await ctx.send(f"Team '{team_name}' created with {ctx.author.mention} as captain!")
    await update_team_panel(ctx)

@bot.command(name='join', help='Join a team')
async def join_team(ctx, team_name):
    global teams, team_members
    team_name = team_name.upper().strip()
    if ctx.author.id in team_members:
        await ctx.send("You're already in a team!")
        return
    if team_name not in teams:
        await ctx.send("Team doesn't exist!")
        return
    teams[team_name]["members"].add(ctx.author.id)
    team_members[ctx.author.id] = team_name
    await ctx.send(f"{ctx.author.mention} has joined {team_name}!")
    await update_team_panel(ctx)

@bot.command(name='leave', help='Leave your current team')
async def leave_team(ctx):
    global teams, team_members
    if ctx.author.id not in team_members:
        await ctx.send("You're not in any team!")
        return
    team_name = team_members[ctx.author.id]
    teams[team_name]["members"].remove(ctx.author.id)
    del team_members[ctx.author.id]
    if len(teams[team_name]["members"]) == 0:
        del teams[team_name]
    await ctx.send(f"{ctx.author.mention} has left {team_name}!")
    await update_team_panel(ctx)

@bot.command(name='reset', help='Reset all teams')
async def reset_teams(ctx):
    global teams, team_members, team_panel_message
    teams = {}
    team_members = {}
    if team_panel_message:
        await team_panel_message.delete()
        team_panel_message = None
    await ctx.send("All teams have been reset!")

@bot.command(name='credits', help='Get information about the creator of this bot')
async def credit(ctx):
    description = (
        "This bot was created by **Jonathan Rojas**, a NErDy Alumni from Francisco Bravo Medical Magnet "
        "High School, Class of 2024. He is currently a 1st-year undergraduate student at UCSD studying Chemistry. "
        "Jonathan developed this bot to help you practice buzzing for Science Bowl. Enjoy and happy buzzing!"
    )

    embed = discord.Embed(
        title="✨ Bot Credits ✨",
        description=description,
        color=discord.Color.gold()  # Changed the color to gold for a more appealing look
    )

    embed.set_thumbnail(url="https://example.com/path/to/jonathan_profile_image.jpg")  # Optional: Add a thumbnail image if available
    embed.set_footer(text="Science Bowl Bot by Jonathan Rojas")

    await ctx.send(embed=embed)

@bot.command(name='about', help='Learn how to use the bot')
async def about(ctx):
    about_text = (
        "**Science Bowl Bot**\n"
        "Created by Jonathan Rojas with his totally awesome Python skills! 🐍\n\n"
        "**Team Commands:**\n"
        "- `!create [team name]` - Create a team (max 2)\n"
        "- `!join [team name]` - Join an existing team\n"
        "- `!leave` - Leave your current team\n"
        "- `!start` - Start a game with current teams\n"
        "- `!end` - End the game and show results\n"
        "- `!reset` - Reset all teams\n\n"
        "**Game Commands:**\n"
        "- `!question` - Get a random question\n"
        "- `!skip` - Skip current question\n"
        "- `buzz [answer]` - Answer the current question\n\n"
        "**Information Commands:**\n"
        "- `!credits` - Get information about the creator of this bot\n"
        "- `!altair` - Credits Altair Maine as the inspiration for this bot\n\n"
        "**Category Commands:**\n"
        "`!astro`, `!es`, `!math`, `!energy`, `!bio`, `!chem`, `!physics`, `!gen`\n\n"
        "Enjoy competitive Science Bowl! 🚀"
    )

    embed = discord.Embed(
        title="About Science Bowl Bot",
        description=about_text,
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)

@bot.command(name='altair', help='Credits Altair Maine as the inspiration for this bot.')
async def altair(ctx, image_url: str = "https://www.ioes.ucla.edu/wp-content/uploads/2017/06/altair-maine-600x540.jpeg"):
    intro = (
        "**Altair Maine** was an inspiration for the creation of this Discord bot. "
        "His dedication to teaching and supporting students in various competitions inspired the image and purpose of this bot."
    )

    short_description = (
        "Altair Maine is a math and science teacher at North Hollywood High School. "
        "He coordinates most of the extracurricular activities in the science department and supports students in various competitions."
    )

    long_description = (
        "Altair Maine went to college at 11 and entered a Caltech doctoral program at 16. At 22, he was the youngest person to coach an academic decathlon team in the state.\n\n"
        "Although he often dressed in a shirt and tie, the baby-faced coach of North Hollywood High School’s so-called 'acadeca' team was often mistaken for a student. "
        "But after leading the team to a second-place finish in the Los Angeles Unified School District competition, opponents were taking him seriously as the first day of the California Academic Decathlon began in Modesto.\n\n"
        "Today, Altair continues to coach North Hollywood to the highest level of Science Bowl at the national competition. He supports students participating in competitions like Science Olympiad, Science Bowl, Ocean Sciences Bowl, Robotics, and various Olympiads. "
        "Altair is highly respected for his commitment and sense of purpose, choosing to be a public school teacher over lucrative offers in computer programming."
    )

    description = f"{intro}\n\n{short_description}\n\n{long_description}"
    embed = discord.Embed(title="About Altair Maine", description=description, color=discord.Color.blue())

    if image_url:
        embed.set_thumbnail(url=image_url)

    await ctx.send(embed=embed)

@bot.command(name='start', help='Start the game')
async def start_game(ctx):
    global game_active
    if len(teams) < 2:
        await ctx.send("Need at least 2 teams to start!")
        return
    game_active[ctx.channel.id] = True
    await ctx.send("Game started! First tossup coming up...")
    await fetch_question(ctx.channel, game_mode=True)

@bot.command(name='end', help='End the game')
async def end_game(ctx):
    global game_active
    if not game_active.get(ctx.channel.id, False):
        await ctx.send("No active game to end!")
        return
    game_active[ctx.channel.id] = False
    if pending_answers[ctx.channel.id]["active"]:
        pending_answers[ctx.channel.id]["active"] = False
        if pending_answers[ctx.channel.id]["timer_task"]:
            pending_answers[ctx.channel.id]["timer_task"].cancel()
    winner = max(teams.keys(), key=lambda team: teams[team]["points"])

    final_scores = "\n".join(f"{team}: {teams[team]['points']}" for team in teams)

    embed = discord.Embed(
        title="🏁 Game Ended! Final Scores:",
        description=f"{final_scores}\n\n🎉 Winner: {winner}!",
        color=discord.Color.gold()
    )

    await ctx.send(embed=embed)
    await reset_teams(ctx)

async def run_timer(channel, duration, phase):
    channel_id = channel.id
    question_message = pending_answers[channel_id].get('question_message')
    if not question_message:
        return

    for remaining in range(duration, 0, -1):
        if not pending_answers[channel_id]["active"]:
            return
        embed = question_message.embeds[0]
        embed.set_field_at(1, name="Timer", value=f"Time remaining: {remaining} seconds")
        await question_message.edit(embed=embed)
        await asyncio.sleep(1)

    if pending_answers[channel_id]["active"]:
        pending_answers[channel_id]["active"] = False
        await channel.send(f"⏰ Time's up! Correct answer was: **{pending_answers[channel_id]['answer']}**")
        if pending_answers[channel_id]["game_mode"]:
            await fetch_question(channel, game_mode=True)

async def update_team_panel(ctx):
    global team_panel_message
    if len(teams) == 0:
        if team_panel_message:
            await team_panel_message.delete()
            team_panel_message = None
        return

    team_info = "\n".join([f"**{team}**: {', '.join([ctx.guild.get_member(uid).mention for uid in teams[team]['members']])}" for team in teams])
    description = (
        f"{team_info}\n\n"
        "Waiting for teams to do `!start`\n\n"
        "**How to Play:**\n"
        "- Use `!create [team name]` to create a team (max 2)\n"
        "- Use `!join [team name]` to join an existing team\n"
        "- Use `!leave` to leave your current team\n"
        "- Use `!start` to start the game\n"
    )

    embed = discord.Embed(
        title="🏁 Waiting for Teams",
        description=description,
        color=discord.Color.blue()
    )

    if team_panel_message:
        await team_panel_message.edit(embed=embed)
    else:
        team_panel_message = await ctx.send(embed=embed)

async def fetch_question(channel, category=None, sources=None, game_mode=False, phase="tossup", bonus_team=None):
    try:
        channel_id = channel.id
        if channel_id in pending_answers and pending_answers[channel_id].get("active", False):
            await channel.send("A question is already active! Wait until it's answered or use !skip to end it.")
            return

        if not game_mode:
            phase = "bonus" if random.choice([True, False]) else "tossup"

        while True:
            response = get_question_by_category(category)
            if response.status_code == 200:
                data = response.json()
                if "question" in data:
                    question_data = data["question"]
                    question_category = question_data["category"]

                    if question_category == EXCLUDED_CATEGORY:
                        continue

                    if category and question_category not in category:
                        continue

                    if phase == "tossup":
                        question = question_data["tossup_question"]
                        answer = question_data["tossup_answer"]
                        bonus_question = question_data.get("bonus_question", "")
                        bonus_answer = question_data.get("bonus_answer", "")
                    else:
                        question = question_data["bonus_question"]
                        answer = question_data["bonus_answer"]
                        bonus_question = ""
                        bonus_answer = ""

                    question_id = question_data.get("id", "")
                    q_type, clean_answer, word_answer = parse_answer(answer, question_data.get("source"))

                    pending_answers[channel_id] = {
                        "answer": clean_answer,
                        "type": q_type,
                        "word_answer": word_answer,
                        "active": True,
                        "answered_users": set(),
                        "wrong_teams": set(),
                        "phase": phase,
                        "game_mode": game_mode,
                        "source": question_data.get("source"),
                        "bonus_team": bonus_team,
                        "bonus_question": bonus_question,
                        "bonus_answer": bonus_answer,
                        "category": question_category,
                        "question_id": question_id,
                        "question_message": None,
                        "timer_task": None
                    }

                    emoji = CATEGORY_EMOJIS.get(question_category, "")
                    color = CATEGORY_COLORS.get(question_category, discord.Color.blue())
                    source_url = f"https://scibowldb.com/tossup/{question_id}" if phase == "tossup" else f"https://scibowldb.com/bonus/{question_id}"

                    embed = discord.Embed(
                        title=f"{emoji} {question_category} Question",
                        description=question,
                        color=color
                    )
                    embed.add_field(name="Source", value=f"[{question_data.get('source', 'N/A')}]({source_url})", inline=True)

                    if game_mode:
                        embed.add_field(name="Timer", value=f"Time remaining: {15 if phase == 'tossup' else 30} seconds", inline=True)
                    embed.set_footer(text="Type 'buzz' followed by your answer!")
                    question_message = await channel.send(embed=embed)
                    pending_answers[channel_id]['question_message'] = question_message

                    if game_mode:
                        timer_duration = 15 if phase == "tossup" else 30
                        timer_task = asyncio.create_task(run_timer(channel, timer_duration, phase))
                        pending_answers[channel_id]['timer_task'] = timer_task

                    break
            else:
                await channel.send(f"API Error: HTTP {response.status_code}")
                break

    except Exception as e:
        print(f"Error: {e}")
        await channel.send("There was an error processing your request.")


@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if message.channel.id in pending_answers and pending_answers[message.channel.id].get("active", False):
        data = pending_answers[message.channel.id]
        user, content = message.author, message.content.strip().upper()

        if not content.startswith("BUZZ"):
            await bot.process_commands(message)
            return

        user_answer = content[4:].strip().upper()
        is_correct = validate_answer(user_answer, data["answer"], data["type"], data.get("word_answer"), data.get("source"))

        if data["game_mode"]:
            if user.id not in team_members:
                await message.reply("❌ You need to be in a team to answer!")
                return

            team_name = team_members[user.id]

            if data["phase"] == "tossup":
                if team_name in data["wrong_teams"]:
                    await message.reply("❌ Your team already answered incorrectly!")
                    return

                if user.id in data["answered_users"]:
                    await message.reply("❌ You already answered this question!")
                    return

                data["answered_users"].add(user.id)

                if is_correct:
                    teams[team_name]["points"] += 4
                    await message.channel.send(f"✅ **{team_name}** answered correctly! (+4 points) 🔥")

                    user_streaks[user.id] = user_streaks.get(user.id, 0) + 1
                    streak_message = f"🔥 Streak: {user_streaks[user.id]}"
                    await message.channel.send(streak_message)

                    await message.channel.send(embed=format_points())

                    pending_answers[message.channel.id]["active"] = False
                    if data["timer_task"]:
                        data["timer_task"].cancel()

                    await fetch_question(message.channel, category=data["category"], game_mode=True, phase="bonus", bonus_team=team_name)
                else:
                    data["wrong_teams"].add(team_name)
                    await message.channel.send(f"❌ **{team_name}** answered incorrectly!")

                    user_streaks[user.id] = 0

                    if len(data["wrong_teams"]) >= len(teams):
                        await message.channel.send(
                            f"🏁 All teams missed! Correct answer: ||{data['answer']}||\n",
                            embed=format_points()
                        )
                        pending_answers[message.channel.id]["active"] = False
                        if data["timer_task"]:
                            data["timer_task"].cancel()
                        await fetch_question(message.channel, game_mode=True)
                    else:
                        await message.channel.send(embed=format_points())
                        if data["timer_task"]:
                            data["timer_task"].cancel()
                        timer_task = asyncio.create_task(run_timer(message.channel, 15, "tossup"))
                        pending_answers[message.channel.id]['timer_task'] = timer_task

            elif data["phase"] == "bonus":
                if team_name != data["bonus_team"]:
                    await message.reply("❌ Only the bonus team can answer this question!")
                    return

                if is_correct:
                    teams[team_name]["points"] += 10
                    await message.channel.send(f"🎉 **{team_name}** bonus correct! (+10 points) 🔥")

                    user_streaks[user.id] = user_streaks.get(user.id, 0) + 1
                    streak_message = f"🔥 Streak: {user_streaks[user.id]}"
                    await message.channel.send(streak_message)
                else:
                    await message.channel.send(f"❌ **{team_name}** bonus answer incorrect! The correct answer was: **{data['bonus_answer']}**")

                    user_streaks[user.id] = 0

                pending_answers[message.channel.id]["active"] = False
                if data["timer_task"]:
                    data["timer_task"].cancel()

                await message.channel.send(embed=format_points())
                await fetch_question(message.channel, game_mode=True)
        else:
            if is_correct:
                await message.channel.send(f"✅ Correct answer! The answer was: **{data['answer']}** 🔥")

                user_streaks[user.id] = user_streaks.get(user.id, 0) + 1
                streak_message = f"🔥 Streak: {user_streaks[user.id]}"
                await message.channel.send(streak_message)
            else:
                await message.channel.send(f"❌ Incorrect answer. The correct answer was: **{data['answer']}**")

                user_streaks[user.id] = 0

            pending_answers[message.channel.id]["active"] = False

    await bot.process_commands(message)

def validate_answer(user_answer, correct_answer, q_type, word_answer=None, source=None):
    user_answer = user_answer.upper()
    if q_type == "mcq":
        if source == "98Nats":
            # For "98Nats" source, only match the part before the "--"
            correct_answer = correct_answer.split('--')[0].strip()
        return user_answer == correct_answer
    else:
        # Collect all acceptable answers
        corrects = [correct_answer.upper()]
        if word_answer:
            # Split comma-separated alternatives
            alternatives = [alt.strip().upper() for alt in word_answer.split(',')]
            corrects.extend(alternatives)

        # Check for similarity match first
        if any(is_similar(user_answer, ans) for ans in corrects):
            return True

        # Check for word matches
        correct_words = []
        for answer in corrects:
            correct_words.extend(answer.split())

        user_words = user_answer.split()

        # Check if any correct word appears in user's answer
        return any(word in user_words for word in correct_words)

def format_points():
    points = "\n".join([f"{team}: {teams[team]['points']} pts" for team in teams])
    embed = discord.Embed(
        title="📊 Current Points:",
        description=points,
        color=discord.Color.blue()
    )
    return embed

@bot.event
async def on_ready():
    print(f'{bot.user.name} has connected to Discord!')

if __name__ == '__main__':
    import nest_asyncio
    nest_asyncio.apply()
    bot.run(TOKEN)