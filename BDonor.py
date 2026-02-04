import asyncio
import aiosqlite
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import csv
import os
from datetime import datetime

api_id = 0000
api_hash = "0000"
BOT_TOKEN = "0000"
SESSION_NAME = "BDonor"

ADMIN_GROUP_ID = -1000000
CHANNEL_ID = -1000000
BOT_CHANNEL_LINK = "https://t.me/0000"

BLOOD_GROUPS = ["O-", "O+", "A+", "A-", "B+", "B-", "AB+", "AB-"]

app = Client(SESSION_NAME,
             api_id=api_id, api_hash=api_hash,
             bot_token=BOT_TOKEN)
user_states = {}

# ---------------- DATABASE ----------------


async def init_db():
    async with aiosqlite.connect("blood.db") as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS donors (
                userid INTEGER PRIMARY KEY,
                blood_group TEXT,
                phone TEXT
            )
        """)
        await db.commit()

# ---------------- START ----------------


@app.on_message(filters.command("start"))
async def start(client, message):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🩸 Donor", callback_data="role_donor")],
        [InlineKeyboardButton("🏥 Recipient", callback_data="role_recipient")]
    ])
    await message.reply("Please choose your role:", reply_markup=keyboard)

# ---------------- ROLE SELECTION ----------------


@app.on_callback_query(filters.regex("^role_"))
async def role_handler(client, query):
    role = query.data.split("_")[1]
    user_states[query.from_user.id] = {"role": role}

    if role == "donor":
        await ask_blood_group(query)
    else:
        await ask_recipient_blood(query)

# ---------------- DONOR FLOW ----------------


async def ask_blood_group(query):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(
            bg, callback_data=f"donor_bg_{bg}") for bg in BLOOD_GROUPS[i:i+2]]
        for i in range(0, len(BLOOD_GROUPS), 2)
    ])
    await query.message.edit_text("Select your blood group:", reply_markup=keyboard)


@app.on_callback_query(filters.regex("^donor_bg_"))
async def donor_blood_handler(client, query):
    bg = query.data.replace("donor_bg_", "")
    user_states[query.from_user.id]["blood_group"] = bg
    user_states[query.from_user.id]["step"] = "donor_phone"
    await query.message.edit_text("Please send your phone number:")


# ---------------- USER REPLY ----------------

@app.on_message(filters.private & filters.reply & filters.text)
async def recipient_reply_handler(client, message):
    uid = message.from_user.id
    data = user_states.get(uid)

    if not data or not data.get("locked"):
        return

    await client.forward_messages(
        chat_id=ADMIN_GROUP_ID,
        from_chat_id=uid,
        message_ids=message.id
    )

# ---------------- TEXT HANDLER ----------------


@app.on_message(filters.private & filters.text & ~filters.reply)
async def text_handler(client, message):
    uid = message.from_user.id
    data = user_states.get(uid)

    if data and data.get("locked"):
        return
    if uid not in user_states:
        return
    state = user_states[uid]

    # ---- Donor Phone ----
    if state.get("step") == "donor_phone":
        phone = message.text
        bg = state["blood_group"]

        async with aiosqlite.connect("blood.db") as db:
            await db.execute(
                "INSERT OR REPLACE INTO donors (userid, blood_group, phone) VALUES (?, ?, ?)",
                (uid, bg, phone)
            )
            await db.commit()

        await message.reply(
            f"🙏 Thank you for registering as a donor!\n\n"
            f"📢 Please join our channel for updates:\n{BOT_CHANNEL_LINK}"
        )
        user_states.pop(uid)

    # ---- Recipient Flow ----
    elif state.get("step") == "recipient_name":
        state["name"] = message.text
        state["step"] = "recipient_place"
        await message.reply("📍 Send the place:")

    elif state.get("step") == "recipient_place":
        state["place"] = message.text
        state["step"] = "recipient_phone"
        await message.reply("📞 Send phone number:")

    elif state.get("step") == "recipient_phone":
        state["phone"] = message.text
        state["step"] = "recipient_count"
        await message.reply("👥 Number of needed donors:")

    elif state.get("step") == "recipient_count":
        state["count"] = message.text
        await message.reply("Your request under review")
        await send_to_admins(client, uid)

# ---------------- RECIPIENT FLOW ----------------


async def ask_recipient_blood(query):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(
            bg, callback_data=f"rec_bg_{bg}") for bg in BLOOD_GROUPS[i:i+2]]
        for i in range(0, len(BLOOD_GROUPS), 2)
    ] + [[InlineKeyboardButton("🩸 Platelets", callback_data="rec_bg_platelets")]])

    await query.message.edit_text("Select required blood group:", reply_markup=keyboard)


@app.on_callback_query(filters.regex("^rec_bg_"))
async def recipient_blood_handler(client, query):
    bg = query.data.replace("rec_bg_", "")
    user_states[query.from_user.id].update({
        "blood_group": bg,
        "step": "recipient_name"
    })
    await query.message.edit_text("👤 Send patient name:")

# ---------------- ADMIN VERIFICATION ----------------


async def send_to_admins(client, uid):
    data = user_states[uid]
    text = (
        f"🩸 Blood Request Verification\n\n"
        f"👤 Name: {data['name']}\n"
        f"🆔 Account: "
        f"<a href='tg://user?id={uid}'>{data['name']}</a>\n\n"
        f"🩸 Blood Group: {data['blood_group']}\n"
        f"📍 Place: {data['place']}\n"
        f"📞 Phone: {data['phone']}\n"
        f"👥 Needed: {data['count']}"
    )

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Agree", callback_data=f"approve_{uid}"),
            InlineKeyboardButton("❌ Disagree", callback_data=f"reject_{uid}")
        ],
        [
            InlineKeyboardButton(
                "✔ Completed", callback_data=f"admin_completed_{uid}")
        ]
    ])

    admin_msg = await client.send_message(ADMIN_GROUP_ID, text, reply_markup=keyboard)
    data["admin_message_id"] = admin_msg.id
    data["locked"] = True

# ---------------- ADMIN REPLY ----------------


@app.on_message(filters.chat(ADMIN_GROUP_ID) & filters.reply & filters.text)
async def admin_reply_handler(client, message):
    replied = message.reply_to_message

    for uid, data in user_states.items():
        if data.get("admin_message_id") == replied.id:
            await client.send_message(
                uid,
                f"📩 **Message from the blood donation team:**\n\n{message.text}"
            )
            break


# ---------------- USER REPLY ----------------

@app.on_message(filters.private & filters.reply & filters.text)
async def recipient_reply_handler(client, message):
    uid = message.from_user.id
    data = user_states.get(uid)

    if not data or not data.get("locked"):
        return

    await client.forward_messages(
        chat_id=ADMIN_GROUP_ID,
        from_chat_id=uid,
        message_ids=message.id
    )


# ---------------- APPROVAL ----------------


@app.on_callback_query(filters.regex("^(approve|reject)_"))
async def admin_decision(client, query):
    action, uid = query.data.split("_")
    uid = int(uid)

    if action == "reject":
        await client.send_message(uid, "❌ Your request was rejected.")
        user_states.pop(uid, None)
        return

    data = user_states[uid]
    data["approved"] = True
    await client.send_message(
        uid,
        "✅ Your request is approved.\nPress Completed after finishing.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(
             "✔ Completed", callback_data=f"completed_{uid}")]
        ])
    )

    await notify_donors(client, data)

# ---------------- NOTIFY DONORS ----------------


async def notify_donors(client, data):
    text = (
        f"🩸 Urgent Blood Request\n\n"
        f"Name: {data['name']}\n"
        f"Blood Group: {data['blood_group']}\n"
        f"Place: {data['place']}\n"
        f"Phone: {data['phone']}\n"
        f"Needed: {data['count']}"
    )

    async with aiosqlite.connect("blood.db") as db:
        if data["blood_group"].lower() == "platelets":
            async with db.execute("SELECT userid FROM donors") as cursor:
                async for row in cursor:
                    await client.send_message(row[0], text)
        else:
            async with db.execute(
                "SELECT userid FROM donors WHERE blood_group = ?",
                (data["blood_group"],)
            ) as cursor:
                async for row in cursor:
                    await client.send_message(row[0], text)

    channel_msg = await client.send_message(CHANNEL_ID, text)
    data["channel_message_id"] = channel_msg.id
    data["channel_message_text"] = text

# ---------------- COMPLETED ----------------


@app.on_callback_query(filters.regex("^completed_"))
async def completed_handler(client, query):
    uid = int(query.data.replace("completed_", ""))

    data = user_states.get(uid)
    if not data:
        return

    if data.get("completed"):
        return

    new_text = (
        data["channel_message_text"]
        + "\n\n✅ **COMPLETED**"
    )

    await client.edit_message_text(
        chat_id=CHANNEL_ID,
        message_id=data["channel_message_id"],
        text=new_text
    )

    data["locked"] = False

    await query.message.edit_text("✔ Marked as completed. Thank you.")
    for key in [
        "admin_message_id",
        "channel_message_id",
        "channel_message_text",
        "approved",
        "completed"
    ]:
        data.pop(key, None)

# ---------------- COMPLETED ADMIN ----------------


@app.on_callback_query(filters.regex("^admin_completed_"))
async def admin_completed_handler(client, query):
    uid = int(query.data.replace("admin_completed_", ""))

    data = user_states.get(uid)
    if not data:
        await query.answer("Request not found.", show_alert=True)
        return

    if not data.get("approved"):
        await query.answer("Request not approved yet.", show_alert=True)
        return

    if data.get("completed"):
        await query.answer("Already completed.", show_alert=True)
        return

    data["completed"] = True

    new_text = (
        data["channel_message_text"]
        + "\n\n✅ **COMPLETED**"
    )

    await client.edit_message_text(
        chat_id=CHANNEL_ID,
        message_id=data["channel_message_id"],
        text=new_text
    )

    data["locked"] = False

    await query.message.edit_text("✔ Marked as completed by admin.")

    for key in [
        "admin_message_id",
        "channel_message_id",
        "channel_message_text",
        "approved",
        "completed"
    ]:
        data.pop(key, None)

# ---------------- DASH ----------------


@app.on_message(filters.chat(ADMIN_GROUP_ID) & filters.command("dash"))
async def dashboard_handler(client, message):
    async with aiosqlite.connect("blood.db") as db:
        # Total donors
        async with db.execute("SELECT COUNT(*) FROM donors") as cursor:
            total = (await cursor.fetchone())[0]

        # Count per blood group
        async with db.execute(
            "SELECT blood_group, COUNT(*) FROM donors GROUP BY blood_group"
        ) as cursor:
            rows = await cursor.fetchall()

    text = "📊 **Blood Donation Dashboard**\n\n"
    text += f"👥 **Total Donors:** {total}\n\n"

    for bg, count in rows:
        text += f"🩸 **{bg}** : {count}\n"

    await message.reply(text)

# ---------------- EXPORT ----------------


@app.on_message(filters.chat(ADMIN_GROUP_ID) & filters.command("export"))
async def export_donors_handler(client, message):

    filename = f"donors_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    async with aiosqlite.connect("blood.db") as db:
        async with db.execute(
            "SELECT userid, blood_group, phone FROM donors"
        ) as cursor:
            rows = await cursor.fetchall()

    if not rows:
        await message.reply("⚠️ No donors found in database.")
        return

    # Write CSV
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["User ID", "Blood Group", "Phone"])
        writer.writerows(rows)

    # Send file to admin group
    await client.send_document(
        chat_id=ADMIN_GROUP_ID,
        document=filename,
        caption="📤 Donors database export"
    )

    # Clean up file
    os.remove(filename)

# ---------------- RUN ----------------


async def init():
    await init_db()

asyncio.get_event_loop().run_until_complete(init())
print("Bot is running...")
app.run()
