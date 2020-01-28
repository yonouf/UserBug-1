# Copyright (C) 2019 The Raphielscape Company LLC.
#
# Licensed under the Raphielscape Public License, Version 1.c (the "License");
# you may not use this file except in compliance with the License.
"""
Userbot module to help you manage a group
"""

from asyncio import sleep
from os import remove

from telethon.errors import (BadRequestError, ChatAdminRequiredError,
                             ImageProcessFailedError, PhotoCropSizeSmallError,
                             UserAdminInvalidError)
from telethon.errors.rpcerrorlist import (UserIdInvalidError,
                                          MessageTooLongError)
from telethon.tl.functions.channels import (EditAdminRequest,
                                            EditBannedRequest,
                                            EditPhotoRequest)
from telethon.tl.functions.messages import UpdatePinnedMessageRequest
from telethon.tl.types import (PeerChannel, ChannelParticipantsAdmins,
                               ChatAdminRights, ChatBannedRights,
                               MessageEntityMentionName, MessageMediaPhoto,
                               ChannelParticipantsBots)

from userbot import BOTLOG, BOTLOG_CHATID, CMD_HELP, bot
from userbot.events import register

# =================== CONSTANT ===================
PP_TOO_SMOL = "The image is too small"
PP_ERROR = "Failure while processing the image"
NO_ADMIN = "I am not an admin!"
NO_PERM = "I don't have sufficient permissions!"
NO_SQL = "Running on Non-SQL mode!"

CHAT_PP_CHANGED = "Chat Picture Changed"
CHAT_PP_ERROR = "Some issue with updating the pic," \
                "maybe coz I'm not an admin," \
                "or don't have enough rights."
INVALID_MEDIA = "Invalid Extension"

BANNED_RIGHTS = ChatBannedRights(
    until_date=None,
    view_messages=True,
    send_messages=True,
    send_media=True,
    send_stickers=True,
    send_gifs=True,
    send_games=True,
    send_inline=True,
    embed_links=True,
)

UNBAN_RIGHTS = ChatBannedRights(
    until_date=None,
    send_messages=None,
    send_media=None,
    send_stickers=None,
    send_gifs=None,
    send_games=None,
    send_inline=None,
    embed_links=None,
)

MUTE_RIGHTS = ChatBannedRights(until_date=None, send_messages=True)

UNMUTE_RIGHTS = ChatBannedRights(until_date=None, send_messages=False)
# ================================================


@register(outgoing=True, pattern="^.gppppppppp$")
async def set_group_photo(gpic):
    """ For .setgpic command, changes the picture of a group """
    if not gpic.is_group:
        await gpic.edit("I don't think this is a group.")
        return
    replymsg = await gpic.get_reply_message()
    chat = await gpic.get_chat()
    admin = chat.admin_rights
    creator = chat.creator
    photo = None

    if not admin and not creator:
        await gpic.edit(NO_ADMIN)
        return

    if replymsg and replymsg.media:
        if isinstance(replymsg.media, MessageMediaPhoto):
            photo = await gpic.client.download_media(message=replymsg.photo)
        elif "image" in replymsg.media.document.mime_type.split('/'):
            photo = await gpic.client.download_file(replymsg.media.document)
        else:
            await gpic.edit(INVALID_MEDIA)

    if photo:
        try:
            await gpic.client(
                EditPhotoRequest(gpic.chat_id, await
                                 gpic.client.upload_file(photo)))
            await gpic.edit(CHAT_PP_CHANGED)

        except PhotoCropSizeSmallError:
            await gpic.edit(PP_TOO_SMOL)
        except ImageProcessFailedError:
            await gpic.edit(PP_ERROR)


@register(outgoing=True, pattern="^.pro(?: |$)(.*)")
async def promote(promt):
    """ For .promote command, promotes the replied/tagged person """
    # Get targeted chat
    chat = await promt.get_chat()
    # Grab admin status or creator in a chat
    admin = chat.admin_rights
    creator = chat.creator

    # If not admin and not creator, also return
    if not admin and not creator:
        await promt.edit(NO_ADMIN)
        return

    new_rights = ChatAdminRights(add_admins=False,
                                 invite_users=True,
                                 change_info=False,
                                 ban_users=True,
                                 delete_messages=True,
                                 pin_messages=True)

    await promt.edit("Upgrading...")
    user, rank = await get_user_from_event(promt)
    if not rank:
        rank = "Administrator"  # Just in case.
    if user:
        pass
    else:
        return

    # Try to promote if current user is admin or creator
    try:
        await promt.client(
            EditAdminRequest(promt.chat_id, user.id, new_rights, rank))
        await promt.edit("Upgraded!")

    # If Telethon spit BadRequestError, assume
    # we don't have Promote permission
    except BadRequestError:
        await promt.edit(NO_PERM)
        return

    # Announce to the logging group if we have promoted successfully
    if BOTLOG:
        await promt.client.send_message(
            BOTLOG_CHATID, "#PROMOTE\n"
            f"USER: [{user.first_name}](tg://user?id={user.id})\n"
            f"CHAT: {promt.chat.title}({promt.chat_id})")


@register(outgoing=True, pattern="^.dem(?: |$)(.*)")
async def demote(dmod):
    """ For .demote command, demotes the replied/tagged person """
    # Admin right check
    chat = await dmod.get_chat()
    admin = chat.admin_rights
    creator = chat.creator

    if not admin and not creator:
        await dmod.edit(NO_ADMIN)
        return

    # If passing, declare that we're going to demote
    await dmod.edit("Downgrading...")
    rank = "admeme"  # dummy rank, lol.
    user = await get_user_from_event(dmod)
    user = user[0]
    if user:
        pass
    else:
        return

    # New rights after demotion
    newrights = ChatAdminRights(add_admins=None,
                                invite_users=None,
                                change_info=None,
                                ban_users=None,
                                delete_messages=None,
                                pin_messages=None)
    # Edit Admin Permission
    try:
        await dmod.client(
            EditAdminRequest(dmod.chat_id, user.id, newrights, rank))

    # If we catch BadRequestError from Telethon
    # Assume we don't have permission to demote
    except BadRequestError:
        await dmod.edit(NO_PERM)
        return
    await dmod.edit("Downgraded!")

    # Announce to the logging group if we have demoted successfully
    if BOTLOG:
        await dmod.client.send_message(
            BOTLOG_CHATID, "#DEMOTE\n"
            f"USER: [{user.first_name}](tg://user?id={user.id})\n"
            f"CHAT: {dmod.chat.title}({dmod.chat_id})")


@register(outgoing=True, pattern="^.b(?: |$)(.*)")
async def ban(bon):
    """ For .ban command, bans the replied/tagged person """
    # Here laying the sanity check
    chat = await bon.get_chat()
    admin = chat.admin_rights
    creator = chat.creator

    # Well
    if not admin and not creator:
        await bon.edit(NO_ADMIN)
        return

    user, reason = await get_user_from_event(bon)
    if user:
        pass
    else:
        return

    # Announce that we're going to whack the pest
    await bon.edit("Whacking the pest!")

    try:
        await bon.client(EditBannedRequest(bon.chat_id, user.id,
                                           BANNED_RIGHTS))
    except BadRequestError:
        await bon.edit(NO_PERM)
        return
    # Helps ban group join spammers more easily
    try:
        reply = await bon.get_reply_message()
        if reply:
            await reply.delete()
    except BadRequestError:
        await bon.edit(
            "I dont have message nuking rights! But still he was banned!")
        return
    # Delete message and then tell that the command
    # is done gracefully
    # Shout out the ID, so that fedadmins can fban later
    if reason:
        await bon.edit(f"{str(user.id)} was banned !!\nReason: {reason}")
    else:
        await bon.edit(f"{str(user.id)} was banned !!")
    # Announce to the logging group if we have banned the person
    # successfully!
    if BOTLOG:
        await bon.client.send_message(
            BOTLOG_CHATID, "#BAN\n"
            f"USER: [{user.first_name}](tg://user?id={user.id})\n"
            f"CHAT: {bon.chat.title}({bon.chat_id})")


@register(outgoing=True, pattern="^.ub(?: |$)(.*)")
async def nothanos(unbon):
    """ For .unban command, unbans the replied/tagged person """
    # Here laying the sanity check
    chat = await unbon.get_chat()
    admin = chat.admin_rights
    creator = chat.creator

    # Well
    if not admin and not creator:
        await unbon.edit(NO_ADMIN)
        return

    # If everything goes well...
    await unbon.edit("Unbanning...")

    user = await get_user_from_event(unbon)
    user = user[0]
    if user:
        pass
    else:
        return

    try:
        await unbon.client(
            EditBannedRequest(unbon.chat_id, user.id, UNBAN_RIGHTS))
        await unbon.edit("Unbanned!")

        if BOTLOG:
            await unbon.client.send_message(
                BOTLOG_CHATID, "#UNBAN\n"
                f"USER: [{user.first_name}](tg://user?id={user.id})\n"
                f"CHAT: {unbon.chat.title}({unbon.chat_id})")
    except UserIdInvalidError:
        await unbon.edit("Uh oh my unban logic broke!")


@register(outgoing=True, pattern="^.m(?: |$)(.*)")
async def spider(spdr):
    """
    This function is basically muting peeps
    """
    # Check if the function running under SQL mode
    try:
        from userbot.modules.sql_helper.spam_mute_sql import mute
    except AttributeError:
        await spdr.edit(NO_SQL)
        return

    # Admin or creator check
    chat = await spdr.get_chat()
    admin = chat.admin_rights
    creator = chat.creator

    # If not admin and not creator, return
    if not admin and not creator:
        await spdr.edit(NO_ADMIN)
        return

    user, reason = await get_user_from_event(spdr)
    if user:
        pass
    else:
        return

    self_user = await spdr.client.get_me()

    if user.id == self_user.id:
        await spdr.edit(
            "Hands too short, can't duct tape myself...\n(ヘ･_･)ヘ┳━┳")
        return

    # If everything goes well, do announcing and mute
    await spdr.edit("S T F U !")
    if mute(spdr.chat_id, user.id) is False:
        return await spdr.edit('Error! User already muted.')
    else:
        try:
            await spdr.client(
                EditBannedRequest(spdr.chat_id, user.id, MUTE_RIGHTS))

            # Announce that the function is done
            if reason:
                await spdr.edit(f"S T F U ! Reason: {reason}")
            else:
                await spdr.edit("S T F U !")

            # Announce to logging group
            if BOTLOG:
                await spdr.client.send_message(
                    BOTLOG_CHATID, "#MUTE\n"
                    f"USER: [{user.first_name}](tg://user?id={user.id})\n"
                    f"CHAT: {spdr.chat.title}({spdr.chat_id})")
        except UserIdInvalidError:
            return await spdr.edit("Uh oh my mute logic broke!")


@register(outgoing=True, pattern="^.um(?: |$)(.*)")
async def unmoot(unmot):
    """ For .unmute command, unmute the replied/tagged person """
    # Admin or creator check
    chat = await unmot.get_chat()
    admin = chat.admin_rights
    creator = chat.creator

    # If not admin and not creator, return
    if not admin and not creator:
        await unmot.edit(NO_ADMIN)
        return

    # Check if the function running under SQL mode
    try:
        from userbot.modules.sql_helper.spam_mute_sql import unmute
    except AttributeError:
        await unmot.edit(NO_SQL)
        return

    # If admin or creator, inform the user and start unmuting
    await unmot.edit('Unmuting...')
    user = await get_user_from_event(unmot)
    user = user[0]
    if user:
        pass
    else:
        return

    if unmute(unmot.chat_id, user.id) is False:
        return await unmot.edit("Error! User probably already unmuted.")
    else:

        try:
            await unmot.client(
                EditBannedRequest(unmot.chat_id, user.id, UNBAN_RIGHTS))
            await unmot.edit("Unmuted")
        except UserIdInvalidError:
            await unmot.edit("Uh oh my unmute logic broke!")
            return

        if BOTLOG:
            await unmot.client.send_message(
                BOTLOG_CHATID, "#UNMUTE\n"
                f"USER: [{user.first_name}](tg://user?id={user.id})\n"
                f"CHAT: {unmot.chat.title}({unmot.chat_id})")


@register(incoming=True)
async def muter(moot):
    """ Used for deleting the messages of muted people """
    try:
        from userbot.modules.sql_helper.spam_mute_sql import is_muted
        from userbot.modules.sql_helper.gmute_sql import is_gmuted
    except AttributeError:
        return
    muted = is_muted(moot.chat_id)
    gmuted = is_gmuted(moot.sender_id)
    rights = ChatBannedRights(
        until_date=None,
        send_messages=True,
        send_media=True,
        send_stickers=True,
        send_gifs=True,
        send_games=True,
        send_inline=True,
        embed_links=True,
    )
    if muted:
        for i in muted:
            if str(i.sender) == str(moot.sender_id):
                await moot.delete()
                await moot.client(
                    EditBannedRequest(moot.chat_id, moot.sender_id, rights))
    for i in gmuted:
        if i.sender == str(moot.sender_id):
            await moot.delete()


@register(outgoing=True, pattern="^.ugmmmmmmm(?: |$)(.*)")
async def ungmoot(un_gmute):
    """ For .ungmute command, ungmutes the target in the userbot """
    # Admin or creator check
    chat = await un_gmute.get_chat()
    admin = chat.admin_rights
    creator = chat.creator

    # If not admin and not creator, return
    if not admin and not creator:
        await un_gmute.edit(NO_ADMIN)
        return

    # Check if the function running under SQL mode
    try:
        from userbot.modules.sql_helper.gmute_sql import ungmute
    except AttributeError:
        await un_gmute.edit(NO_SQL)
        return

    user = await get_user_from_event(un_gmute)
    user = user[0]
    if user:
        pass
    else:
        return

    # If pass, inform and start ungmuting
    await un_gmute.edit('Ungmuting...')

    if ungmute(user.id) is False:
        await un_gmute.edit("Error! User probably not gmuted.")
    else:
        # Inform about success
        await un_gmute.edit("Ungmuted Successfully")

        if BOTLOG:
            await un_gmute.client.send_message(
                BOTLOG_CHATID, "#UNGMUTE\n"
                f"USER: [{user.first_name}](tg://user?id={user.id})\n"
                f"CHAT: {un_gmute.chat.title}({un_gmute.chat_id})")


@register(outgoing=True, pattern="^.gmmmmmmm(?: |$)(.*)")
async def gspider(gspdr):
    """ For .gmute command, globally mutes the replied/tagged person """
    # Admin or creator check
    chat = await gspdr.get_chat()
    admin = chat.admin_rights
    creator = chat.creator

    # If not admin and not creator, return
    if not admin and not creator:
        await gspdr.edit(NO_ADMIN)
        return

    # Check if the function running under SQL mode
    try:
        from userbot.modules.sql_helper.gmute_sql import gmute
    except AttributeError:
        await gspdr.edit(NO_SQL)
        return

    user, reason = await get_user_from_event(gspdr)
    if user:
        pass
    else:
        return

    # If pass, inform and start gmuting
    await gspdr.edit("Grabs a huge, sticky duct tape!")
    if gmute(user.id) is False:
        await gspdr.edit(
            'Error! User probably already gmuted.\nRe-rolls the tape.')
    else:
        if reason:
            await gspdr.edit(f"Globally taped!Reason: {reason}")
        else:
            await gspdr.edit("Globally taped!")

        if BOTLOG:
            await gspdr.client.send_message(
                BOTLOG_CHATID, "#GMUTE\n"
                f"USER: [{user.first_name}](tg://user?id={user.id})\n"
                f"CHAT: {gspdr.chat.title}({gspdr.chat_id})")


@register(outgoing=True, pattern="^.zo(?: |$)(.*)", groups_only=False)
async def rm_deletedacc(show):
    """ For .zombies command, list all the ghost/deleted/zombie accounts in a chat. """

    con = show.pattern_match.group(1).lower()
    del_u = 0
    del_status = "No Zombies found, Group is clean"

    if con != "clean":
        await show.edit("Searching Zombie accounts...")
        async for user in show.client.iter_participants(show.chat_id):

            if user.deleted:
                del_u += 1
                await sleep(1)
        if del_u > 0:
            del_status = f"Found **{del_u}** Zombie account(s), clean them by using .zo clean"
        await show.edit(del_status)
        return

    # Here laying the sanity check
    chat = await show.get_chat()
    admin = chat.admin_rights
    creator = chat.creator

    # Well
    if not admin and not creator:
        await show.edit("I am not an admin")
        return

    await show.edit("Deleting Zombie accounts...Awesome")
    del_u = 0
    del_a = 0

    async for user in show.client.iter_participants(show.chat_id):
        if user.deleted:
            try:
                await show.client(
                    EditBannedRequest(show.chat_id, user.id, BANNED_RIGHTS))
            except ChatAdminRequiredError:
                await show.edit("I don't have ban rights in this group")
                return
            except UserAdminInvalidError:
                del_u -= 1
                del_a += 1
            await show.client(
                EditBannedRequest(show.chat_id, user.id, UNBAN_RIGHTS))
            del_u += 1


    if del_u > 0:
        del_status = f"Cleaned **{del_u}** Zombie account(s)"

    if del_a > 0:
        del_status = f"Cleaned **{del_u}** Zombie account(s) **{del_a}** deleted admin accounts are not removed"


    await show.edit(del_status)
    await sleep(2)
    await show.delete()


    if BOTLOG:
        await show.client.send_message(
            BOTLOG_CHATID, "#CLEANUP\n"
            f"Cleaned **{del_u}** deleted account(s) !!\
            \nCHAT: {show.chat.title}({show.chat_id})")



@register(outgoing=True, pattern="^.ads$")
async def get_admin(show):
    """ For .admins command, list all of the admins of the chat. """
    info = await show.client.get_entity(show.chat_id)
    title = info.title if info.title else "this chat"
    mentions = f'<b>Admins in {title}:</b> \n'
    try:
        async for user in show.client.iter_participants(
                show.chat_id, filter=ChannelParticipantsAdmins):
            if not user.deleted:
                link = f"<a href=\"tg://user?id={user.id}\">{user.first_name}</a>"
                userid = f"<code>{user.id}</code>"
                mentions += f"\n{link} {userid}"
            else:
                mentions += f"\nDeleted Account <code>{user.id}</code>"
    except ChatAdminRequiredError as err:
        mentions += " " + str(err) + "\n"
    await show.edit(mentions, parse_mode="html")


@register(outgoing=True, pattern="^.pin(?: |$)(.*)")
async def pin(msg):
    """ For .pin command, pins the replied/tagged message on the top the chat. """
    # Admin or creator check
    chat = await msg.get_chat()
    admin = chat.admin_rights
    creator = chat.creator

    # If not admin and not creator, return
    if not admin and not creator:
        await msg.edit(NO_ADMIN)
        return

    to_pin = msg.reply_to_msg_id

    if not to_pin:
        await msg.edit("Reply to a message to pin it.")
        return

    options = msg.pattern_match.group(1)

    is_silent = True

    if options.lower() == "loud":
        is_silent = False

    try:
        await msg.client(
            UpdatePinnedMessageRequest(msg.to_id, to_pin, is_silent))
    except BadRequestError:
        await msg.edit(NO_PERM)
        return

    await msg.edit("Pinned!")

    user = await get_user_from_id(msg.from_id, msg)

    if BOTLOG:
        await msg.client.send_message(
            BOTLOG_CHATID, "#PIN\n"
            f"ADMIN: [{user.first_name}](tg://user?id={user.id})\n"
            f"CHAT: {msg.chat.title}({msg.chat_id})\n"
            f"LOUD: {not is_silent}")


@register(outgoing=True, pattern="^.k(?: |$)(.*)")
async def kick(usr):
    """ For .kick command, kicks the replied/tagged person from the group. """
    # Admin or creator check
    chat = await usr.get_chat()
    admin = chat.admin_rights
    creator = chat.creator

    # If not admin and not creator, return
    if not admin and not creator:
        await usr.edit(NO_ADMIN)
        return

    user, reason = await get_user_from_event(usr)
    if not user:
        await usr.edit("Couldn't fetch user.")
        return

    await usr.edit("Kicking...")

    try:
        await usr.client.kick_participant(usr.chat_id, user.id)
        await sleep(.5)
    except Exception as e:
        await usr.edit(NO_PERM + f"\n{str(e)}")
        return

    if reason:
        await usr.edit(
            f"Kicked [{user.first_name}](tg://user?id={user.id})! Reason: {reason}"
        )
    else:
        await usr.edit(
            f"Kicked [{user.first_name}](tg://user?id={user.id})!")

    if BOTLOG:
        await usr.client.send_message(
            BOTLOG_CHATID, "#KICK\n"
            f"USER: [{user.first_name}](tg://user?id={user.id})\n"
            f"CHAT: {usr.chat.title}({usr.chat_id})\n")


@register(outgoing=True, pattern="^.us ?(.*)")
async def get_users(show):
    """ For .users command, list all of the users in a chat. """
    info = await show.client.get_entity(show.chat_id)
    title = info.title if info.title else "this chat"
    mentions = 'Users in {}: \n'.format(title)
    try:
        if not show.pattern_match.group(1):
            async for user in show.client.iter_participants(show.chat_id):
                if not user.deleted:
                    mentions += f"\n[{user.first_name}](tg://user?id={user.id}) {user.id}"
                else:
                    mentions += f"\nDeleted Account {user.id}"
        else:
            searchq = show.pattern_match.group(1)
            async for user in show.client.iter_participants(
                    show.chat_id, search=f'{searchq}'):
                if not user.deleted:
                    mentions += f"\n[{user.first_name}](tg://user?id={user.id}) {user.id}"
                else:
                    mentions += f"\nDeleted Account {user.id}"
    except ChatAdminRequiredError as err:
        mentions += " " + str(err) + "\n"
    try:
        await show.edit(mentions)
    except MessageTooLongError:
        await show.edit(
            "Damn, this is a huge group. Uploading users lists as file.")
        file = open("userslist.txt", "w+")
        file.write(mentions)
        file.close()
        await show.client.send_file(
            show.chat_id,
            "userslist.txt",
            caption='Users in {}'.format(title),
            reply_to=show.id,
        )
        remove("userslist.txt")


async def get_user_from_event(event):
    """ Get the user from argument or replied message. """
    args = event.pattern_match.group(1).split(' ', 1)
    extra = None
    if event.reply_to_msg_id and not len(args) == 2:
        previous_message = await event.get_reply_message()
        user_obj = await event.client.get_entity(previous_message.from_id)
        extra = event.pattern_match.group(1)
    elif args:
        user = args[0]
        if len(args) == 2:
            extra = args[1]

        if user.isnumeric():
            user = int(user)

        if not user:
            await event.edit("Pass the user's username, id or reply!")
            return

        if event.message.entities is not None:
            probable_user_mention_entity = event.message.entities[0]

            if isinstance(probable_user_mention_entity,
                          MessageEntityMentionName):
                user_id = probable_user_mention_entity.user_id
                user_obj = await event.client.get_entity(user_id)
                return user_obj
        try:
            user_obj = await event.client.get_entity(user)
        except (TypeError, ValueError) as err:
            await event.edit(str(err))
            return None

    return user_obj, extra


async def get_user_from_id(user, event):
    if isinstance(user, str):
        user = int(user)

    try:
        user_obj = await event.client.get_entity(user)
    except (TypeError, ValueError) as err:
        await event.edit(str(err))
        return None

    return user_obj

  
@register(outgoing=True, pattern="^.deleeeeeeeeeee ?(.*)")
async def get_usersdel(show):
    """ For .usersdel command, list all of the deleted users in a chat. """
    info = await show.client.get_entity(show.chat_id)
    title = info.title if info.title else "this chat"
    mentions = 'deletedUsers in {}: \n'.format(title)
    try:
        if not show.pattern_match.group(1):
            async for user in show.client.iter_participants(show.chat_id):
                if not user.deleted:
                    mentions += f"\n[{user.first_name}](tg://user?id={user.id}) {user.id}"
         #       else:
    #                mentions += f"\nDeleted Account {user.id}"
        else:
            searchq = show.pattern_match.group(1)
            async for user in show.client.iter_participants(
                   show.chat_id, search=f'{searchq}'):
                if not user.deleted:
                    mentions += f"\n[{user.first_name}](tg://user?id={user.id}) {user.id}"
         #       else:
      #              mentions += f"\nDeleted Account {user.id}"
    except ChatAdminRequiredError as err:
        mentions += " " + str(err) + "\n"
    try:
        await show.edit(mentions)
    except MessageTooLongError:
        await show.edit(
            "Damn, this is a huge group. Uploading deletedusers lists as file.")
        file = open("userslist.txt", "w+")
        file.write(mentions)
        file.close()
        await show.client.send_file(
            show.chat_id,
            "deleteduserslist.txt",
            caption='Users in {}'.format(title),
            reply_to=show.id,
        )
        remove("deleteduserslist.txt")


async def get_userdel_from_event(event):
    """ Get the deleted user from argument or replied message. """
    args = event.pattern_match.group(1).split(' ', 1)
    extra = None
    if event.reply_to_msg_id and not len(args) == 2:
        previous_message = await event.get_reply_message()
        user_obj = await event.client.get_entity(previous_message.from_id)
        extra = event.pattern_match.group(1)
    elif args:
        user = args[0]
        if len(args) == 2:
            extra = args[1]

        if user.isnumeric():
            user = int(user)

        if not user:
            await event.edit("Pass the deleted user's username, id or reply!")
            return

        if event.message.entities is not None:
            probable_user_mention_entity = event.message.entities[0]

            if isinstance(probable_user_mention_entity,
                          MessageEntityMentionName):
                user_id = probable_user_mention_entity.user_id
                user_obj = await event.client.get_entity(user_id)
                return user_obj
        try:
            user_obj = await event.client.get_entity(user)
        except (TypeError, ValueError) as err:
            await event.edit(str(err))
            return None

    return user_obj, extra


async def get_userdel_from_id(user, event):
    if isinstance(user, str):
        user = int(user)

    try:
        user_obj = await event.client.get_entity(user)
    except (TypeError, ValueError) as err:
        await event.edit(str(err))
        return None

    return user_obj

@register(outgoing=True, pattern="^.botssssssssssssssss$", groups_only=True)
async def get_bots(show):
    """ For .bots command, list all of the bots of the chat. """
    info = await show.client.get_entity(show.chat_id)
    title = info.title if info.title else "this chat"
    mentions = f'<b>Bots in {title}:</b>\n'
    try:
        if isinstance(message.to_id, PeerChat):
            await show.edit("I heard that only Supergroups can have bots.")
            return
        else:
            async for user in show.client.iter_participants(
                    show.chat_id, filter=ChannelParticipantsBots):
                if not user.deleted:
                    link = f"<a href=\"tg://user?id={user.id}\">{user.first_name}</a>"
                    userid = f"<code>{user.id}</code>"
                    mentions += f"\n{link} {userid}"
                else:
                    mentions += f"\nDeleted Bot <code>{user.id}</code>"
    except ChatAdminRequiredError as err:
        mentions += " " + str(err) + "\n"
    try:
        await show.edit(mentions, parse_mode="html")
    except MessageTooLongError:
        await show.edit(
            "Damn, too many bots here. Uploading bots list as file.")
        file = open("botlist.txt", "w+")
        file.write(mentions)
        file.close()
        await show.client.send_file(
            show.chat_id,
            "botlist.txt",
            caption='Bots in {}'.format(title),
            reply_to=show.id,
        )
        remove("botlist.txt")

@register(outgoing=True, pattern="^.menu$")
async def dumtyer(dumtter):
    await dumtter.edit("⊙ Tap [𝕄𝔼ℕ𝕌](https://telegra.ph/Menu-01-28) to See All Available Commands ⊙")


@register(outgoing=True, pattern="^.admin$")
async def dumper(dumber):
  await dumber.edit("⊙ 𝐀𝐃𝐌𝐈𝐍 ⊙\n\n⊙ .k ⊙ .b ⊙ .ub ⊙ .pin ⊙ .m ⊙ .um ⊙ .lo ⊙ .ul ⊙ .pro ⊙ .dem ⊙ .zo ⊙ .ads ⊙ .us ⊙\n⊙ Help : .h 𝐀𝐃𝐌𝐈𝐍 for Details ⊙")
    
CMD_HELP.update({
  "admin":
  "⊙ 𝐀𝐃𝐌𝐈𝐍 ⊙\n\n"
  "⊙ .ads .us : Admins & Users Lists ⊙ .b .ub : Ban & Unban ⊙"
  " .k : Kick ⊙ .pin : Pin Messages ⊙ .m .um : Mute & Unmute ⊙"
  " .pro .dem : Promote & Demote ⊙ .zo : Scan & Clean Zombies ⊙"
  " .lo .ul : Lock & Unlock ⊙ Types : all, msg, media, sticker, gif,"
  "game, inline, poll, invite, pin, info ⊙"})

@register(outgoing=True, pattern="^.apps$")
async def dumcer(dumder):
    await dumder.edit("⊙ 𝐀𝐏𝐏𝐒 ⊙\n\n⊙ .i ⊙ .g ⊙ .im ⊙ .wi ⊙ .cu ⊙ .ud ⊙ .tt ⊙ .tr ⊙ .la ⊙ .y ⊙ .ss ⊙ .film ⊙\n⊙ Help : .h 𝐀𝐏𝐏𝐒 for Details ⊙")

CMD_HELP.update({
	"apps":
	"⊙ 𝐀𝐏𝐏𝐒 ⊙\n\n"
	"⊙ .i Image ⊙ .g Google ⊙ .im Imdb ⊙ .wi Wikipedia ⊙"
	" .y YouTube ⊙ .cu Currency ⊙ .ud Dictionary ⊙"
	" .tt Text To Speech ⊙ .tr Translate ⊙ .la Language ⊙"
	" .ss ScreenShot ⊙ .film Dunia21 ⊙"})
                      
@register(outgoing=True, pattern="^.chats$")
async def dumver(dumyer):
    await dumyer.edit("⊙ 𝐂𝐇𝐀𝐓𝐒 ⊙\n\n⊙ .pu ⊙ .purgeme ⊙ .d ⊙ .sd ⊙ .app ⊙ .dap ⊙ .bl ⊙ .ubl ⊙\n⊙ Help : .h 𝐂𝐇𝐀𝐓𝐒 for Details ⊙")

CMD_HELP.update({
  "chats":
	"⊙ 𝐂𝐇𝐀𝐓𝐒 ⊙\n\n"
	"⊙ .pu Purge ⊙ .purgeme Purge Me ⊙"
	" .d Delete ⊙ .sd Self Destruction ⊙"
	" .app Approves PM ⊙ .dap Disapproves PM ⊙"
	" .bl Blocks PM ⊙ .ubl Unblocks PM ⊙"})

@register(outgoing=True, pattern="^.download$")
async def dumoer(dumocer):
    await dumocer.edit("⊙ 𝐃𝐎𝐖𝐍𝐋𝐎𝐀𝐃 ⊙\n\n⊙ .ar ⊙ .aw ⊙ .dw ⊙ .upd ⊙ .up ⊙ .uas ⊙ .ria ⊙ .riv ⊙ .gd ⊙ .li ⊙ .di ⊙ .am ⊙ .at ⊙ .sgd ⊙ .au ⊙ .ac ⊙ .ap ⊙\n⊙ Help : .h 𝐃𝐎𝐖𝐍𝐋𝐎𝐀𝐃 for Details ⊙")
    
CMD_HELP.update({
	"download":
	"⊙ 𝐃𝐎𝐖𝐍𝐋𝐎𝐀𝐃 ⊙\n\n"
	"⊙ .dw Download ⊙ .upd Uploadir ⊙ .up Upload ⊙ .uas Upload as ⊙ .at Torrent ⊙"
	" .au URL ⊙ .am Magnet ⊙ .ac Clear ⊙ .ap Pause ⊙ .ar Resume ⊙ .aw Show ⊙"
	" .gd Upload to GD ⊙ .li Files on GD ⊙ .sgd Set GD ⊙ .ria Rip Audio ⊙ .riv Rip Video ⊙"
	" .di Direct URLs GDrive Mega CMail Yandex AFH Zippy MF SF OSDN GitHub ⊙"})

@register(outgoing=True, pattern="^.sgd$")
async def dumier(dumoler):
    await dumoler.edit("⊙ 𝐆𝐃𝐑𝐈𝐕𝐄 ⊙\n\
		       \n⊙ .gd file_path / reply / URL|file_name ⊙\
		       \n⊙ Usage: Uploads the file in reply, URL or file path in server to your GDrive ⊙\
		       \n⊙ .li query ⊙\
		       \n⊙ Usage : Looks for files and folders in your GDrive ⊙\
		       \n⊙ .gsetf GDrive Folder URL ⊙\
		       \n⊙ Usage : Sets the folder to upload new files to ⊙\
		       \n⊙ .gsetclear ⊙\
		       \n⊙ Usage : Reverts to default upload destination ⊙\
		       \n⊙ .gfolder ⊙\
		       \n⊙ Usage : Shows your current upload destination/folder ⊙\
		       \n⊙ .ggd path_to_folder_in_server ⊙\
		       \n⊙ Usage : Uploads all the files in the directory to a folder in GDrive ⊙")

@register(outgoing=True, pattern="^.info$")
async def dumler(dumger):
    await dumger.edit("⊙ 𝐈𝐍𝐅𝐎 ⊙\n\n⊙ .dc ⊙ .speed ⊙ .w ⊙ .sys ⊙ .pip ⊙ .who ⊙ .com ⊙ .sup ⊙ .rp ⊙ .dvc  ⊙ .cn ⊙ .spc ⊙ .git ⊙ .co ⊙ .u ⊙ .t ⊙ .bv ⊙ .sleep ⊙ .shutdown ⊙ .restart ⊙\n⊙ Help : .h 𝐈𝐍𝐅𝐎 for Details ⊙")

CMD_HELP.update({
  "info":
	"⊙ 𝐈𝐍𝐅𝐎 ⊙\n\n"
	"⊙ .dc Datacentre ⊙ .speed Test ⊙ .w Weather ⊙ .sys System ⊙"
	" .bv Version ⊙ .who Whois ⊙ .co Count Username ⊙ .git Search ⊙"
	" .pip Search ⊙ .cn Codename ⊙ .dvc Device ⊙ .spc Specs ⊙"
	" .sleep Bot ⊙ .com Community ⊙ .sup Support ⊙ .u Update ⊙"
	" .shutdown BOT ⊙ .restart BOT ⊙ .t Terminal ⊙"})
                      
@register(outgoing=True, pattern="^.memes$")
async def dumeer(dumwer):
    await dumwer.edit("⊙ 𝐌𝐄𝐌𝐄𝐒 ⊙\n\n⊙ .rpf ⊙ .acf ⊙ .rcf ⊙ .f ⊙ .ly ⊙ .ty ⊙ .Oof ⊙ .hi ⊙ .str ⊙ .sl ⊙ .ka ⊙ .stk ⊙ .rb ⊙ .ca ⊙ .oub ⊙ .shalom ⊙\n⊙ Help : .h 𝐌𝐄𝐌𝐄𝐒 for Details ⊙")

CMD_HELP.update({
  "memes":
  "⊙ 𝐌𝐄𝐌𝐄𝐒 ⊙\n\n"
  "⊙ .rpf Lydia reply ⊙ .acf Lydia add ⊙ .rcf Lydia Remove ⊙ .ly Fake Link ⊙"
  " .ty Type ⊙ .sl Slaps ⊙ .str Stretch ⊙ .f Big f**k ⊙ .hi Say Hai ⊙"
  " .ka Kang Stickers ⊙ .stk Stickers Info ⊙ .rb Remove BG ⊙ .ca Carbon ⊙"
  " .oub OpenUserBot ⊙ .shalom Shalom ⊙"})

@register(outgoing=True, pattern="^.note$")
async def dumqer(dumker):
    await dumker.edit("⊙ 𝐍𝐎𝐓𝐄 ⊙\n\n⊙ .notes ⊙ .clear ⊙ .save ⊙ .rmn ⊙ .sw ⊙ .cw ⊙ .rw ⊙ .fi ⊙ .st ⊙ .fs ⊙ .rmf ⊙ .sn ⊙ .si ⊙ .rs ⊙ .tl ⊙\n⊙ Help : .h 𝐍𝐎𝐓𝐄 for Details ⊙")

CMD_HELP.update({
    "note":
    "⊙ 𝐍𝐎𝐓𝐄 ⊙\n\n"
    "⊙ .fi Filter ⊙ .st Stop Filter ⊙ .fs List Filters ⊙ .rmf Remove Bot Filters ⊙"
    " .notes Notes ⊙ .clear Notes ⊙ .save Notes ⊙ .rmn Removes All Bot Notes ⊙"
    " .sw Set Welcome ⊙ .cw Check Welcome ⊙ .rw Remove Welcome ⊙"
    " .sn Snip ⊙ .si Snips ⊙ .rs Remove Snips ⊙ .tl Telegraph ⊙"})
