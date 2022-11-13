### By Ryuk ###
### Made By Modifying code from Kakashi's UX For chats database. ###

import os
import shutil
from subprocess import call
from time import time

import yt_dlp
from pyrogram import filters
from userge import Config, Message, get_collection, userge
from userge.utils.exceptions import StopConversation

VID_LIST = get_collection("VID_LIST")
CHANNEL = userge.getCLogger(__name__)

vid_list = []


async def _init() -> None:
    vid_list.clear()
    vid_list.extend([i["chat_id"] async for i in VID_LIST.find()])


@userge.on_cmd(
    "addv",
    about={
        "header": "add chat to Video LIST",
        "usage": "{tr}addv [chat username or id (optional)]",
    },
    allow_bots=False,
    allow_channels=False,
)
async def add_v(message: Message):
    """add chat to Video List."""
    chat_ = message.input_str
    if not chat_:
        chat_ = message.chat.id
    try:
        chat_ = await userge.get_chat(chat_)
    except BaseException:
        await message.edit(f"`Provided input ({chat_}) is not a chat...`", del_in=5)
        return
    chat_type = chat_.type
    if chat_type == "private":
        chat_name = full_name(chat_)
    else:
        chat_name = chat_.title
    chat_id = chat_.id
    found = await VID_LIST.find_one({"chat_id": chat_id})
    if found:
        await message.edit(f"Chat <b>{chat_name}</b> is already in list.", del_in=5)
        return
    await VID_LIST.insert_one(
        {"chat_name": chat_name, "chat_id": chat_id, "chat_type": chat_type}
    )
    msg_ = f"Successfully added <b>{chat_name}</b> (`{chat_id}`) in Video LIST."
    await message.edit(msg_, del_in=5)
    await CHANNEL.log(msg_)
    await _init()


@userge.on_cmd(
    "delv",
    about={
        "header": "delete chat from Video LIST",
        "flags": {
            "-all": "delete all chats from list",
        },
        "usage": "{tr}delv [chat username or id (optional)]",
    },
    allow_bots=False,
    allow_channels=False,
)
async def del_v(message: Message):
    """delete chat from list for Video list"""
    if "-all" in message.flags:
        msg_ = (
            "### <b>DELETING ALL CHATS FROM Video LIST</b> ###\n\n"
            "For confirmation of deleting all chats from Video LIST,\n"
            "please reply with '`Yes, delete all chats in list for video.`' <b>within 10 seconds</b>."
        )
        await message.edit(msg_)
        try:
            async with userge.conversation(message.chat.id, timeout=10) as conv:
                response = await conv.get_response(
                    mark_read=True,
                    filters=(
                        filters.user([one for one in Config.TRUSTED_SUDO_USERS])
                        | filters.me
                    ),
                )
        except (TimeoutError, StopConversation):
            msg_ += "\n\n### Process cancelled as no response given. ###"
            await message.edit(msg_)
            return
        resp = response.text
        if resp == "Yes, delete all chats in list for video.":
            await VID_LIST.drop()
            await message.delete(msg_)
            del_ = "Deleted whole <b>Video LIST</b> successfully."
            await message.edit(del_, del_in=5)
            await CHANNEL.log(del_)
            return await _init()

    chat_ = message.input_str
    if not chat_:
        chat_ = message.chat.id
    try:
        chat_ = await userge.get_chat(chat_)
    except BaseException:
        await message.edit(f"`Provided input ({chat_}) is not a chat...`", del_in=5)
        return
    chat_id = chat_.id
    found = await VID_LIST.find_one({"chat_id": chat_id})
    if found:
        msg_ = f"Successfully removed <b>{found['chat_name']}</b> from Video LIST."
        await VID_LIST.delete_one(found)
        await message.edit(msg_, del_in=5)
        await CHANNEL.log(msg_)
    else:
        await message.edit(f"The chat <b>{chat_id}</b> doesn't exist in Video LIST.")
    return await _init()


@userge.on_cmd(
    "listv",
    about={
        "header": "list chats in Video List",
        "flags": {
            "-id": "list chat IDs as well",
        },
        "usage": "{tr}listv",
    },
    allow_bots=False,
    allow_channels=False,
)
async def list_video(message: Message):
    """list chats in Video list"""
    s_groups = ""
    s_total = 0
    groups = ""
    g_total = 0
    priv = ""
    p_total = 0
    out_ = "List of chats in <b>Video List</b>: [{}]\n\n"
    async for chat_ in VID_LIST.find():
        chat_id = chat_["chat_id"]
        chat_name = chat_["chat_name"]
        type_ = chat_["chat_type"]
        id_ = f"'`{chat_id}`' - " if "-id" in message.flags else ""
        if type_ == "supergroup":
            s_total += 1
            s_groups += f"• [{s_total}] {id_}<b>{chat_name}</b>\n"
        elif type_ == "group":
            g_total += 1
            groups += f"• [{g_total}] {id_}<b>{chat_name}</b>\n"
        else:
            p_total += 1
            priv += f"• [{p_total}] {id_}<b>{chat_name}</b>\n"
    total_ = s_total + g_total + p_total
    out_ += (
        f"<b>Supergroup/s:</b> [{s_total}]\n"
        f"{s_groups}\n"
        f"<b>Normal group/s:</b> [{g_total}]\n"
        f"{groups}\n"
        f"<b>Private chat/s:</b> [{p_total}]\n"
        f"{priv}"
    )
    out_ = out_.format(total_)
    if len(out_) <= 4096:
        await message.edit(out_)
    else:
        link_ = pt("List of chats in Video List.", out_)
        await message.edit(
            f"List of chats in Video List is <a href='{link_}'><b>HERE</b></a>."
        )


@userge.on_message(
    ~filters.edited
    & (
        filters.regex(r"^https://www.instagram.com/reel/*")
        | filters.regex(r"^https://www.instagram.com/tv/*")
        | filters.regex(r"^https://www.instagram.com/p/*")
        | filters.regex(r"https://twitter.com/*")
        | filters.regex(r"^https://youtube.com/shorts/*")
        | filters.regex(r"^https://vm.tiktok.com/*")
        | filters.regex(r"^\.dl*")
    )
)
async def video_dl(userge, message: Message):
    chat_id = message.chat.id
    del_link = True
    if chat_id in vid_list or (
        message.from_user.id == 1503856346 and message.text.startswith(".dl")
    ):
        caption = "Shared by : "
        if message.sender_chat:
                caption += message.author_signature
        else:
                caption += (await userge.get_users(message.from_user.username or message.from_user.id)).first_name
        msg = await message.reply("`Trying to download...`")
        raw_message = message.text.split()
        for link in raw_message:
            if link.startswith("http"):
                startTime = time()
                dl_path = f"downloads/{str(startTime)}"
                try:
                    _opts = {
                        "outtmpl": f"{dl_path}/video.mp4",
                        "format": "bv[ext=mp4]+ba[ext=m4a]/b[ext=mp4]",
                        "prefer_ffmpeg": True,
                        "postprocessors": [{"key": "FFmpegMetadata"}, {"key": "EmbedThumbnail"}],
                    }
                    x=yt_dlp.YoutubeDL(_opts).download(link)
                    video_path = f"{dl_path}/video.mp4"
                    thumb_path = f"{dl_path}/i.jpg"
                    call(
                        f'''ffmpeg -ss 0.1 -i "{video_path}" -vframes 1 "{thumb_path}"''',
                        shell=True,
                    )
                    await userge.send_video(chat_id, video=video_path, thumb=thumb_path, caption=caption)
                    if os.path.exists(str(dl_path)):
                        shutil.rmtree(dl_path)
                except Exception as e:
                    if str(e).startswith("ERROR: [Instagram]"):
                        await msg.edit(
                            "Couldn't download video,\n`trying alternate method....`"
                        )
                        from pyrogram.errors import MediaEmpty, WebpageCurlFailed

                        i_dl = instadl(link)
                        if i_dl == "not found":
                            await message.reply(
                                "Video download failed.\nLink not supported or private."
                            )
                        else:
                            try:
                                await message.reply_video(i_dl, caption=caption)
                            except (MediaEmpty, WebpageCurlFailed):
                                from wget import download

                                x = download(i_dl, "x.mp4")
                                await message.reply_video(x, caption=caption)
                                if os.path.exists(x):
                                    os.remove(x)
                    else:
                        await CHANNEL.log(str(e))
                        await message.reply("**Link not supported or private.** 🥲")
                        del_link = False
                    continue
        await msg.delete()
        if del_link or message.from_user.id == 1503856346:
            await message.delete()


def instadl(url):
    try:
        from selenium import webdriver
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.support.ui import WebDriverWait

        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument("start-maximised")
        chrome_options.binary_location = Config.GOOGLE_CHROME_BIN
        chrome_options.add_argument("ignore-certificate-errors")
        chrome_options.add_argument("test-type")
        chrome_options.add_argument("headless")
        chrome_options.add_argument("no-sandbox")
        chrome_options.add_argument("disable-dev-shm-usage")
        chrome_options.add_argument("no-sandbox")
        chrome_options.add_argument("disable-gpu")
        driver = webdriver.Chrome(chrome_options=chrome_options)
        driver.get(f"https://en.savefrom.net/258/#url={url}")
        link = WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#sf_result .info-box a"))
        )
        rlink = link.get_attribute("href")
    except BaseException:
        rlink = "not found"
    finally:
        driver.close()
        return rlink

def full_name(user: dict):
    try:
        f_name = " ".join([user.first_name, user.last_name or ""])
    except BaseException:
        raise
    return f_name
