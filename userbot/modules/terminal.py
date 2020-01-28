# Copyright (C) 2019 The Raphielscape Company LLC.
#
# Licensed under the Raphielscape Public License, Version 1.c (the "License");
# you may not use this file except in compliance with the License.
#
""" Userbot module for executing code and terminal commands from Telegram. """

import asyncio
from getpass import getuser
from os import remove
from sys import executable
from userbot import CMD_HELP, BOTLOG, BOTLOG_CHATID
from userbot.events import register



@register(outgoing=True, pattern="^.t(?: |$)(.*)")
async def terminal_runner(term):
    """ For .term command, runs bash commands and scripts on your server. """
    curruser = getuser()
    command = term.pattern_match.group(1)
    try:
        from os import geteuid
        uid = geteuid()
    except ImportError:
        uid = "This ain't it chief!"

    if term.is_channel and not term.is_group:
        await term.edit("Term commands aren't permitted on channels!")
        return

    if not command:
        await term.edit("Give a command.")
        return

    if command in ("userbot.session", "config.env"):
        await term.edit("That's a dangerous operation! Not Permitted!")
        return

    process = await asyncio.create_subprocess_shell(
        command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE)
    stdout, stderr = await process.communicate()
    result = str(stdout.decode().strip()) \
        + str(stderr.decode().strip())

    if len(result) > 4096:
        output = open("output.txt", "w+")
        output.write(result)
        output.close()
        await term.client.send_file(
            term.chat_id,
            "output.txt",
            reply_to=term.id,
            caption="Output too large, sending as file",
        )
        remove("output.txt")
        return

    if uid == 0:
        await term.edit("" f"{curruser}:~# {command}" f"\n{result}" "")
    else:
        await term.edit("" f"{curruser}:~$ {command}" f"\n{result}" "")

    if BOTLOG:
        await term.client.send_message(
            BOTLOG_CHATID,
            "Executed",
        )
