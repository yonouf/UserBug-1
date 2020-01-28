# Copyright (C) 2019 The Raphielscape Company LLC.
#
# Licensed under the Raphielscape Public License, Version 1.c (the "License");
# you may not use this file except in compliance with the License.
#
"""
This module updates the userbot based on Upstream revision
"""

from os import remove, execl
import sys

from git import Repo
from git.exc import GitCommandError, InvalidGitRepositoryError, NoSuchPathError

from userbot import CMD_HELP, bot, HEROKU_MEMEZ, HEROKU_APIKEY, HEROKU_APPNAME
from userbot.events import register


async def gen_chlog(repo, diff):
    ch_log = ''
    d_form = "%d/%m/%y"
    for c in repo.iter_commits(diff):
        ch_log += f'•[{c.committed_datetime.strftime(d_form)}]: {c.summary} <{c.author}>\n'
    return ch_log


async def is_off_br(br):
    off_br = ['master']
    for k in off_br:
        if k == br:
            return 1
    return


@register(outgoing=True, pattern="^.u(?: |$)(.*)")
async def upstream(ups):
    "For .update command, check if the bot is up to date, update if specified"
    await ups.edit("Loading...")
    conf = ups.pattern_match.group(1).lower()
    off_repo = 'https://github.com/BL4CKID/UserBug.git'

    try:
        txt = "Oops..Updater cannot continue...\n\n**LOGTRACE:**\n"
        repo = Repo()
    except NoSuchPathError as error:
        await ups.edit(f'{txt}\ndirectory {error} is not found')
        return
    except GitCommandError as error:
        await ups.edit(f'{txt}\nEarly failure! {error}')
        return
    except InvalidGitRepositoryError:
        repo = Repo.init()
        await ups.edit(
            "Warning: Force-Syncing to the latest stable code from repo.\
            \nI may lose my downloaded files during this update."
        )
        origin = repo.create_remote('upstream', off_repo)
        origin.fetch()
        repo.create_head('master', origin.refs.master)
        repo.heads.master.checkout(True)

    ac_br = repo.active_branch.name
    if not await is_off_br(ac_br):
        await ups.edit(
            f'**[UPDATER]:** Looks like you are using your own custom branch ({ac_br}).')
        return

    try:
        repo.create_remote('upstream', off_repo)
    except BaseException:
        pass

    ups_rem = repo.remote('upstream')
    ups_rem.fetch(ac_br)
    changelog = await gen_chlog(repo, f'HEAD..upstream/{ac_br}')

    if not changelog:
        await ups.edit(f'\nYour UserBot is **UP-TO-DATE** with **{ac_br}** Branch from [𝐁𝐋𝟒𝐂𝐊_𝐈𝐃](https://github.com/BL4CKID/UserBug) Repository.\n')
        return

    if conf != "now":
        changelog_str = f'**Update available for [{ac_br}]:\n\nCHANGELOG:**\n{changelog}'
        if len(changelog_str) > 4096:
            await ups.edit("Changelog is too big, sending it as a file.")
            file = open("output.txt", "w+")
            file.write(changelog_str)
            file.close()
            await ups.client.send_file(
                ups.chat_id,
                "output.txt",
                reply_to=ups.id,
            )
            remove("output.txt")
        else:
            await ups.edit(changelog_str)
        await ups.respond(
            "Do \".u now\" to update\nRe-Deploy if using Heroku")
        return

    await ups.edit('Updating...')
    ups_rem.fetch(ac_br)
    await ups.edit('UserBot Updated\n'
                   'Bot is restarting...Wait a seconds...')
    await install_requirements()
    await bot.disconnect()
    # Spin a new instance of bot
    execl(sys.executable, sys.executable, *sys.argv)
    # Shut the existing one down
    exit()

