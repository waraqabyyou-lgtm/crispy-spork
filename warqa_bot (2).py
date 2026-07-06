import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)

BOT_TOKEN  = "8604368429:AAFKkBCpel129tljg14l8qBSGwpEBTPldsk"
OWNER_ID   = 7943160927

PDF_BUNDLE = "bundle.pdf"
PDF_SINGLE = "single.pdf"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

pending_orders = {}

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📦 الباقة الكاملة — 5,000 دج", callback_data="order_bundle")],
        [InlineKeyboardButton("📄 دفتر مفرد — 490 دج",         callback_data="order_single")],
    ]
    await update.message.reply_text(
        "مرحباً بك في ورقة 🗂️\n\n"
        "دفاتر تنظيمية رقمية لأصحاب المشاريع — جاهزة للطبع فوراً.\n\n"
        "اختاري المنتج:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_order_choice(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user    = query.from_user
    product = query.data

    product_name = "الباقة الكاملة (5,000 دج)" if product == "order_bundle" else "دفتر مفرد (490 دج)"
    ccp_number   = "XXXX XXXX XXXX"
    amount       = "5,000 دج" if product == "order_bundle" else "490 دج"

    order_id = f"{user.id}_{product}"
    pending_orders[order_id] = {
        "user_id":  user.id,
        "username": user.username or user.first_name,
        "product":  product
    }
    ctx.user_data["pending_order_id"] = order_id

    await query.edit_message_text(
        f"✅ اخترتِ: {product_name}\n\n"
        f"خطوات الدفع:\n"
        f"1️⃣ حولي {amount} على رقم CCP:\n"
        f"   `{ccp_number}`\n\n"
        f"2️⃣ أرسلي صورة الإيصال هنا مباشرة\n\n"
        f"سيصلك الملف خلال دقائق بعد التحقق ✨",
        parse_mode="Markdown"
    )

async def handle_receipt(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user     = update.message.from_user
    order_id = ctx.user_data.get("pending_order_id")

    if not order_id or order_id not in pending_orders:
        await update.message.reply_text("من فضلك اختاري المنتج أولاً بالضغط على /start")
        return

    order = pending_orders[order_id]
    keyboard = [[
        InlineKeyboardButton("✅ تأكيد — أرسلي الملف", callback_data=f"confirm_{order_id}"),
        InlineKeyboardButton("❌ رفض",                  callback_data=f"reject_{order_id}"),
    ]]
    caption = (
        f"🔔 طلب جديد!\n\n"
        f"👤 الزبون: {order['username']} (ID: {order['user_id']})\n"
        f"📦 المنتج: {'الباقة الكاملة' if order['product'] == 'order_bundle' else 'دفتر مفرد'}\n\n"
        f"هل تأكدتِ من الإيصال؟"
    )
    await ctx.bot.send_photo(
        chat_id      = OWNER_ID,
        photo        = update.message.photo[-1].file_id,
        caption      = caption,
        reply_markup = InlineKeyboardMarkup(keyboard)
    )
    await update.message.reply_text("📨 وصل إيصالك! جاري التحقق...\nسيصلك الملف خلال دقائق ✨")

async def handle_confirm_reject(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data  = query.data

    action, order_id = data.split("_", 1)
    order = pending_orders.get(order_id)

    if not order:
        await query.edit_message_caption("⚠️ الطلب غير موجود أو انتهت صلاحيته.")
        return

    user_id = order["user_id"]
    product = order["product"]

    if action == "confirm":
        pdf_path = PDF_BUNDLE if product == "order_bundle" else PDF_SINGLE
        try:
            with open(pdf_path, "rb") as f:
                await ctx.bot.send_document(
                    chat_id  = user_id,
                    document = f,
                    caption  = "🎉 شكراً على طلبك!\n\nملفك جاهز للتحميل والطبع.\nنتمنالك توفيق في مشروعك 🌟\n\n— ورقة"
                )
            await query.edit_message_caption(f"✅ تم إرسال الملف للزبون {order['username']}")
        except FileNotFoundError:
            await query.edit_message_caption("⚠️ ملف PDF غير موجود — أضيفي الملفات للـ repo.")
            await ctx.bot.send_message(user_id, "عذراً، حدث خطأ تقني. سنتواصل معك قريباً.")
        finally:
            pending_orders.pop(order_id, None)

    elif action == "reject":
        await ctx.bot.send_message(
            user_id,
            "عذراً، لم نتمكن من التحقق من إيصالك.\nمن فضلك أرسلي صورة أوضح أو تواصلي معنا على @warqa.dz"
        )
        await query.edit_message_caption(f"❌ تم رفض طلب {order['username']}")
        pending_orders.pop(order_id, None)

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_order_choice, pattern="^order_"))
    app.add_handler(CallbackQueryHandler(handle_confirm_reject, pattern="^(confirm|reject)_"))
    app.add_handler(MessageHandler(filters.PHOTO, handle_receipt))
    logger.info("ورقة بوت يعمل...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
