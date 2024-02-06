import discord
from functions import parse_times
import os
import paginator
from discord.ext import pages
from functions import plot_enrollment, readcsv, get_overview
from datetime import datetime

class OverviewInputModal(discord.ui.Modal):
    def __init__(self, bot, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        
        self.bot = bot

        self.add_item(discord.ui.InputText(label="Class List (comma separated)", style=discord.InputTextStyle.short))
        self.add_item(discord.ui.InputText(label="First Pass Enrollment Time", style=discord.InputTextStyle.short))
        self.add_item(discord.ui.InputText(label="Second Pass Enrollment Time", style=discord.InputTextStyle.short))

    async def callback(self, interaction: discord.Interaction):
        courses = list(map(str.strip, self.children[0].value.split(',')))
        unreadable = []
        classes = []
        
        for c in courses:
        # check if course is readable; first collapse all spaces and go to uppercase
            course = c.replace(' ', '').upper()

            # reformat to add the space back
            for i in range(2, 5):
                if course[:i].isalpha() and course[i].isdigit():
                    course = course[:i] + ' ' + course[i:]
                    # if unreadable, skip
                    if not os.path.exists(f'../csv/{course}.csv'):
                        print(f'../csv/{course}.csv')
                        unreadable.append(c)
                        continue
                    classes.append(course)
                    break
        print(unreadable)
        print(classes)
        if len(classes)==0:
            em = discord.Embed(title='No results found!', description='Please check your spelling(s) and make sure the classes are properly comma-separated. If this class was not offered last year spring quarter, it will not show up here.')
            em.add_field(name='Usage', value='`/query`')
            em.add_field(name='Your Query', value=f'`{courses}`')
            await interaction.response.send_message(embed=em)
            return
        
        fp_time, sp_time = parse_times(self.children[1].value), parse_times(self.children[2].value)
        
        await self.overview(interaction, classes, fp_time, sp_time)
        
    async def overview(self, interaction, classes: str, first_pass_time: str, second_pass_time: str):

        enrollment_times = (int(first_pass_time), int(second_pass_time))

        # enrollment_times: Tuple[int], contains the first and second pass times in seconds since epoch
        # enrollment_times = (parse_times(first_pass_time), parse_times(second_pass_time))

        # main_em: pages.Page, the first main page to be displayed
        main_em = discord.Embed(title='Overview', description=f'Your first pass time: {datetime.utcfromtimestamp(enrollment_times[0])}\nYour second pass time: {datetime.utcfromtimestamp(enrollment_times[1])}')

        # results: List[pages.Page], to be displayed in the paginator
        results = [pages.Page(embeds=[main_em])]

        # unreadable: List[str], for all invalid courses
        unreadable = []

        # List[str], course lists for each type
        fp_only = []
        sp_only = []
        anytime = []
        waitlist = []
        drop = []

        has_priority_wl = []

        for course in classes:
            if "CSE" in course:
                has_priority_wl.append(course)
            # read course data
            filepath = f'../csv/{course}.csv'
            data = readcsv(filepath)

            # get overview of data and store in result
            result = get_overview(data, course, enrollment_times)

            # summary: List[str], stores results to be used in embed's course summary
            summary = None

            match result['rec']:
                case 0:
                    summary = ['**No**', '**No**', '**No**']
                    if result['wl_rec'] == 0:
                        waitlist.append(course)
                    else:
                        drop.append(course)
                case 1:
                    summary = ['**Yes**', '**No**', '**No**']
                    fp_only.append(course)
                case 2:
                    summary = ['**Yes**', '**Yes**', '**No**']
                    sp_only.append(course)
                case 3:
                    summary = ['**Yes**', '**Yes**', '**Yes**']
                    anytime.append(course)

            match result['wl_rec']:
                case 0:
                    summary.append('**Likely**')
                case 1:
                    summary.append('**Possible**')
                case 2:
                    summary.append('**Unlikely**')
                case 3:
                    summary.append('**N/A**')

            main_em.add_field(name=course, value=f'First Pass: {summary[0]}\nSecond Pass: {summary[1]}\nClasses Start: {summary[2]}\nOff Waitlist: {summary[3]}', inline=True)
            embed = result['embed']

            # plot the enrollment and store it into the embed
            data_stream = plot_enrollment(data, course, enrollment_times[0], enrollment_times[1])
            data_stream.seek(0)
            chart = discord.File(data_stream, filename=f'{course}.png')
            embed.set_image(
                url=f'attachment://{course}.png'
            )
            results.append(pages.Page(embeds=[embed], files=[chart]))

        rec = []
        if fp_only:
            rec.append(f'You should enroll first pass the following courses:\n**{", ".join(fp_only)}**')
        if sp_only:
            rec.append(f'You can second pass the following courses:\n**{", ".join(sp_only)}**')
        if waitlist:
            rec.append(f'You may need to waitlist the following courses:\n**{", ".join(waitlist)}**')
        if anytime:
            rec.append(f'You can always enroll in the following courses:\n**{", ".join(anytime)}**')
        if drop:
            rec.append(f'Do not expect to get the following courses):\n**{", ".join(drop)}**')
        main_em.add_field(name='Recommendations', value='\n\n'.join(rec), inline=False)
        if unreadable:
            main_em.add_field(name='Invalid Classes', value=f'**{", ".join(unreadable)}**', inline=False)
        if has_priority_wl:
            main_em.add_field(name='Waitlist Priority', value=f"You selected one or more classes which may have major priority ({', '.join(has_priority_wl)}), which means that you may not need to first pass it if you are in the department's major. Please refer to the department's website for more details.")
        msg = paginator.MultiPage(self.bot)
        msg.set_pages(results)
        await msg.paginate(interaction)