import sqlite3
from datetime import datetime, timedelta, timezone
import discord
from discord.ext import tasks

from ..const import BOT
from ..utils import write_json
from ..db import get_json_data, check_user_verified, delete_user, check_user_exists
from ..functions.search import search

from .paginator import MultiPage

# ----------------------------------------- begin setup ------------------------------------------ #

verification_timers = {}

def start_verification_timer(discord_user_id, ctx):
    deadline = datetime.now(timezone.utc) + timedelta(minutes=30)
    verification_timers[discord_user_id] = {'deadline': deadline, 'ctx': ctx}
    if len(verification_timers) == 1:
        print("[Routine] Starting verification loop")
        check_verification_status.start()

@tasks.loop(seconds=15)
async def check_verification_status():
    if not verification_timers:
        print(f"[Routine] Stopping routine: no more verifications active.")
        check_verification_status.cancel()
        return
    verify_list = [(k, v) for k, v in verification_timers.items()]
    for discord_user_id, user_data in verify_list:
        print(f"[Routine] Checking verification of user id {discord_user_id}")

        ctx: discord.ApplicationContext = user_data['ctx']
        deadline = user_data['deadline']
        if check_user_verified(discord_user_id):
            await ctx.send_followup(embed=discord.Embed(
                title = "Success!",
                description = "Your PID has been verified successfully!",
                color = discord.Color.green()
            ))
            print(f"[Routine] Verified user id {discord_user_id}")
            verification_timers.pop(discord_user_id, None)
            continue
        if datetime.now(timezone.utc) > deadline:
            await ctx.send_followup(embed=discord.Embed(
                title = "Timeout",
                description = "No audit has been uploaded. Canceling link...",
                color = discord.Color.yellow()
            ))
            print(f"[Routine] Timeout verification user id {discord_user_id}")
            delete_user(discord_user_id)
            verification_timers.pop(discord_user_id, None)

# ------------------------------------------ end setup ------------------------------------------- #

# ----------------------------------------- bot commands ----------------------------------------- #

@BOT.command(
    name = 'search',
    description = 'Return a list of classes that match your search'
)
async def search(
    ctx: discord.ApplicationContext,
    numbers: str = '',
    keywords: str = '',
    dept: str = '',
    division: discord.Option(
        str,
        'Choose an option',
        choices=['All Courses', 'Undergraduate', 'Graduate', 'Upper Division', 'Lower Division']
    ) = 'All Courses' # type: ignore
) -> None:
    courses = search(numbers, keywords, dept, division)
    
    if courses:
        total = len(courses)
        courses = [courses[i:min(i+3, len(courses))] for i in range(0, len(courses), 3)]
        embed_pages = [
            discord.Embed(
                title=f"Search results ({total} total)",
                description=f"Filters: {'\nCourse Codes: ' + numbers if numbers else ''}\n"
                f"Division: {division}{'\nKeywords: ' + keywords if keywords else ''}"
                f"{'\nDepartment: '+dept.strip().upper() if dept else ''}",
                fields=[
                    discord.EmbedField(
                        name = f"{course['code']} | {course['title']}",
                        value = (
                            course['desc']
                            if len(course['desc']) < 1024
                            else course['desc'][:1021] + '...'
                        )
                    )
                    for course in course_section
                ],
                color=discord.Color.blue()
            ) for course_section in courses
        ]
        paginator_cog: MultiPage = BOT.get_cog('MultiPage')
        paginator_cog.set_pages(embed_pages)
        await paginator_cog.paginate(ctx)
    else:
        await ctx.send_response(embed=discord.Embed(
            title = f"Search results (0 total)",
            description = f"Filters: {'\nCourse Codes: ' + numbers if dept else ''}\n"
            f"Division: {division}{'\nKeywords: ' + keywords if dept else ''}"
            f"{'\nDepartment: '+dept.strip().upper() if dept else ''}",
            color = discord.Color.red()
        ))

@BOT.command(
    name = 'me',
    description = 'Get your information.'
)
async def me(ctx: discord.ApplicationContext):
    data = get_json_data(ctx.author.id)
    if not data:
        await ctx.send_response(embed=discord.Embed(
            title='Error',
            description='You are not registered with TritonThink. Use /link to link your UCSD PID!',
            color=discord.Color.red()
        ))
        return
    write_json(f'data/{ctx.author.id}.json', data)
    
    def major_overview(major_data):
        fields = []
        for category in major_data["categories"]:
            value = ''
            for subreq in category['subreqs']:
                value += f'**{subreq['title']}**: '
                match subreq['progress']['type']:
                    case 'complete':
                        value += 'Requirements Complete. ✅\n'
                    case 'units':
                        value += f'{subreq["progress"]["remaining"]} units remaining. 🟥\n'
                    case 'courses':
                        value += f'{subreq["progress"]["remaining"]} courses remaining. 🟥\n'
            
            fields.append(discord.EmbedField(
                name=category['major_category'],
                value=value.rstrip('\n')
            ))
        page = discord.Embed(
            title=major_data['title'],
            fields=fields,
            color=discord.Color.blue()
        )
        return page
    
    def category_overview(category_data):
        fields = []
        for subreq in category_data['subreqs']:
            value = ''
            match subreq['progress']['type']:
                case 'complete':
                    value += 'Requirements Complete. ✅\n'
                case 'units':
                    value += f'{subreq["progress"]["remaining"]} units remaining. 🟥\n'
                case 'courses':
                    value += f'{subreq["progress"]["remaining"]} courses remaining. 🟥\n'
            if subreq['progress']['type'] != 'complete':
                value += f"Choose from: "
                if len(subreq['needed_courses']) > 20:
                    value += ', '.join(subreq['needed_courses'][:20]) + ' or more...'
                else:
                    value += ', '.join(subreq['needed_courses'])
            fields.append(discord.EmbedField(
                name=subreq['title'],
                value=value
            ))
        page = discord.Embed(
            title=category_data['major_category'],
            fields=fields,
            color=discord.Color.blue()
        )
        return page
    embed_pages = []
    if "major" in data:
        embed_pages.append(major_overview(data["major"]))
    if "second_major" in data:
        embed_pages.append(major_overview(data["second_major"]))
    if "major" in data:
        embed_pages.extend(category_overview(category) for category in data["major"]["categories"])
    if "second_major" in data:
        embed_pages.extend(category_overview(category) for category in data["second_major"]["categories"])
    paginator_cog: MultiPage = BOT.get_cog('MultiPage')
    paginator_cog.set_pages(embed_pages)
    await paginator_cog.paginate(ctx)

@BOT.command(
    name = 'link',
    description = 'Link your Discord account to your UCSD PID.'
)
async def link(ctx: discord.ApplicationContext, pid: str):
    pid = pid.upper().strip()
    if len(pid) != 9 or not pid.startswith('A') or not all(c.isdigit() for c in pid[1:]):
        await ctx.send_response(embed=discord.Embed(
            title="Error",
            description=f"The PID provided ({pid}) is invalid.",
            color=discord.Color.red()
        ))
        return
    discord_user_id = str(ctx.author.id)

    try:
        conn = sqlite3.connect('data/users.db')
        cursor = conn.cursor()
        cursor.execute('''
        INSERT INTO users (discord_user_id, pid)
        VALUES (?, ?)
        ON CONFLICT(discord_user_id) DO UPDATE SET pid=excluded.pid
        ''', (discord_user_id, pid))
        
        conn.commit()
        await ctx.send_response(embed=discord.Embed(
            title="Success!",
            description=f"Your PID has been updated to {pid}. Please upload a degree audit within "
            "the next 30 minutes to confirm your PID.",
            color=discord.Color.green()
        ))
        start_verification_timer(discord_user_id, ctx)
    except sqlite3.IntegrityError:
        await ctx.send_response(embed=discord.Embed(
            title="Error",
            description=f"This PID is already linked with another user.",
            color=discord.Color.red()
        ))
    except Exception as e:
        await ctx.send_response(embed=discord.Embed(
            title="Error",
            description=f"Please report this bug to the developers!",
            color=discord.Color.red()
        ))
        print(f"Error while linking: {e}")
    finally:
        conn.close()

@BOT.command(
    name = 'unlink',
    description = 'Unlink your Discord account to your UCSD PID.'
)
async def unlink(ctx: discord.ApplicationContext):
    discord_user_id = str(ctx.author.id)

    try:
        existing = check_user_exists(discord_user_id)

        if existing:
            delete_user(discord_user_id)
            await ctx.send_response(embed=discord.Embed(
                title = "Success!",
                description="Your PID has been unlinked successfully.",
                color=discord.Color.green()
            ))
        else:
            await ctx.send_response(embed=discord.Embed(
                title = "Error",
                description="Your account is not associated with a PID.",
                color=discord.Color.red()
            ))
    except Exception as e:
        await ctx.send_response(embed=discord.Embed(
            title="Error",
            description=f"Please report this bug to the developers!",
            color=discord.Color.red()
        ))
        print(f"Error while unlinking: {e}")

