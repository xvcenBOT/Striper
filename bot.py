import asyncio
import os
from dotenv import load_dotenv
import random
import string
import re
import json
import aiohttp
from datetime import datetime, timedelta

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler
)

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CRYPTO_BOT_TOKEN = os.getenv("CRYPTO_BOT_TOKEN")
BOT_USERNAME = os.getenv("BOT_USERNAME")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
PORT = int(os.getenv("PORT", 8000))

CRYPTO_BOT_API_URL = "https://pay.crypt.bot/api"


def get_price_per_account(quantity):
    if 1 <= quantity < 20:
        return 10
    elif 20 <= quantity < 50:
        return 9
    elif 50 <= quantity <= 100:
        return 8
    else:
        return 10


async def create_crypto_invoice(amount: float, description: str, payload: str):
    url = f"{CRYPTO_BOT_API_URL}/createInvoice"
    
    headers = {
        'Crypto-Pay-API-Token': CRYPTO_BOT_TOKEN,
        'Content-Type': 'application/json'
    }
    
    data = {
        'asset': 'USDT',
        'amount': str(amount),
        'description': description,
        'payload': payload,
        'expires_in': 300
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=data) as response:
            if response.status == 200:
                result = await response.json()
                if result.get('ok'):
                    return result['result']
                else:
                    error_msg = f"API Error: {result.get('error', {}).get('name', 'Unknown error')}"
                    raise Exception(error_msg)
            else:
                response_text = await response.text()
                error_msg = f"HTTP {response.status}: {response_text}"
                raise Exception(error_msg)


async def check_crypto_invoice(invoice_id: str):
    url = f"{CRYPTO_BOT_API_URL}/getInvoices"
    
    headers = {
        'Crypto-Pay-API-Token': CRYPTO_BOT_TOKEN,
        'Content-Type': 'application/json'
    }
    
    data = {
        'invoice_ids': [invoice_id]
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=data) as response:
            if response.status == 200:
                try:
                    result = await response.json()
                    
                    if result.get('ok') and result.get('result') and result.get('result').get('items') and len(result['result']['items']) > 0:
                        invoice_data = result['result']['items'][0]
                        return invoice_data
                    else:
                        return {'status': 'not_found'}
                except json.JSONDecodeError as e:
                    return {'status': 'error', 'error': f'JSON decode error: {e}'}
                except Exception as parse_error:
                    return {'status': 'error', 'error': f'Parse error: {parse_error}'}
            else:
                response_text = await response.text()
                return {'status': 'error', 'error': f"HTTP {response.status}: {response_text}"}


async def check_invoice_timeout(update: Update, context: ContextTypes.DEFAULT_TYPE, invoice_id: str, message_id: int):
    await asyncio.sleep(300)
    
    invoice_data = await check_crypto_invoice(invoice_id)
    if invoice_data.get('status') != 'paid':
        try:
            await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=message_id)
        except Exception:
            pass
        
        timeout_text = (
            "❌ Оплата не была совершена в течение 5 минут.\n"
            "Пожалуйста, начните процесс покупки заново."
        )
        keyboard = [
            [InlineKeyboardButton("◀️ Назад", callback_data='back_to_main_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=timeout_text,
            reply_markup=reply_markup,
            parse_mode='HTML'
        )


def generate_credentials(quantity: int) -> str:
    credentials = []
    for i in range(quantity):
        login = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
        credentials.append(f"Аккаунт {i+1}: {login}: {password}")
    return "\n".join(credentials)


def get_main_menu_data():
    welcome_text = (
        "<b>Добро пожаловать в Stripe Seller Bot ✨</b>\n\n"
        "Давно хотел приобрести качественные Stripe аккаунты с "
        "балансом? Тебе определенно к нам! ⭐\n\n"
        "Ниже располагается меню, ознакомляйся 🎲"
    )

    keyboard = [
        [InlineKeyboardButton("Купить аккаунты 🛒", callback_data='buy_accounts')],
        [
            InlineKeyboardButton("Поддержка 🌐", callback_data='support'),
            InlineKeyboardButton("FAQ ↗️", callback_data='faq')
        ],
        [InlineKeyboardButton("Реферальная система 👥", callback_data='referral_system')],
        [InlineKeyboardButton("Заработать 💰", callback_data='earn_money')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    return welcome_text, reply_markup


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    welcome_text, reply_markup = get_main_menu_data()
    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='HTML')


async def referral_system_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    
    try:
        await query.answer()
    except Exception:
        pass
    
    user_id = query.from_user.id
    bot_username = BOT_USERNAME or "yourbot_username"
    referral_link = f"https://t.me/{bot_username}?start=ref_{user_id}"

    referral_text = (
        "💰 Зарабатывай с нашей реферальной программой!\n"
        f"🔗 Ваша персональная ссылка:\n"
        f"👉 <code>{referral_link}</code>\n\n"
        "🎯 Как это работает?\n"
        "✔ Приглашаешь друзей – делись своей ссылкой.\n"
        "✔ Они покупают – ты получаешь 5% от их заказа.\n"
        "✔ Чем больше рефералов – тем выше пассивный доход!\n\n"
        "📊 Ваша статистика:\n"
        "🔸 Приглашено: 0 человек\n"
        "🔸 Доход с рефералов: растет с каждой покупкой!\n\n"
        "🚀 Начни привлекать клиентов прямо сейчас!\n\n"
        "<i>P.S. 10 друзей = гарантированный профит. А 50? Считай сам! 😉</i>"
    )
    keyboard = [
        [InlineKeyboardButton("Назад", callback_data='back_to_main_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        await query.edit_message_text(
            text=referral_text,
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
    except Exception:
        await query.message.reply_text(
            text=referral_text,
            reply_markup=reply_markup,
            parse_mode='HTML'
        )


async def buy_accounts_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    buy_text = (
        "Шаг 1 из 3... Выбор количества для покупки\n\n"
        "Решил купить аккаунты? Ты на верном пути! ✈️\n"
        "Наши преимущества перед другими сервисами:\n\n"
        "- Мы гарантируем возврат в случае невалидности 🔮\n"
        "- Готовы предоставить платежные системы высшего уровня 💾\n"
        "- Удобные способы оплаты 📥\n"
        "- Быстрая техподдержка, готовая вам помочь в любой момент 📞\n\n"
        "Кхм, перейдем к количеству\n"
        "Вот прайс-лист на аккаунты💎\n\n"
        "От 1 до 20 Штук - 10$💰\n"
        "От 20 до 50 Штук - 9$💰\n"
        "От 50 до 100 Штук - 8$💰\n\n"
        "Нажми на кнопку свое кол-во чтобы приобрести аккаунты либо выбери из готовых паков"
    )

    keyboard = [
        [InlineKeyboardButton("Lite Pack (1 аккаунт)", callback_data='{"action": "select_pack", "quantity": 1}')],
        [InlineKeyboardButton("Starter Pack (3 аккаунта)", callback_data='{"action": "select_pack", "quantity": 3}')],
        [InlineKeyboardButton("Smart Pack (5 аккаунтов)", callback_data='{"action": "select_pack", "quantity": 5}')],
        [InlineKeyboardButton("Pro Pack (10 аккаунтов)", callback_data='{"action": "select_pack", "quantity": 10}')],
        [InlineKeyboardButton("Premium Pack (20 аккаунтов)", callback_data='{"action": "select_pack", "quantity": 20}')],
        [InlineKeyboardButton("Ultimate Pack (30 аккаунтов)", callback_data='{"action": "select_pack", "quantity": 30}')],
        [InlineKeyboardButton("Свое количество", callback_data='{"action": "select_custom_quantity"}')],
        [InlineKeyboardButton("Вернуться назад", callback_data='back_to_buy_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        text=buy_text,
        reply_markup=reply_markup,
        parse_mode='HTML'
    )


def generate_order_id():
    order_id = ''.join(random.choices(string.digits, k=8))
    return order_id


async def handle_pack_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    try:
        data = json.loads(query.data)
        quantity = data.get('quantity')
    except json.JSONDecodeError:
        await query.edit_message_text("Произошла ошибка при обработке данных. Попробуйте снова.", parse_mode='HTML')
        return
    
    price_per_item = get_price_per_account(quantity)
    total_price = quantity * price_per_item
    
    context.user_data['order'] = {
        'quantity': quantity,
        'total_price': total_price
    }

    order_text = (
        "Шаг 2 из 3... Оплата товара\n\n"
        "Ты почти у цели вот твой заказ, все ли верно? ✅\n"
        "🔹 Товар: Stripe Accounts\n"
        f"🔹 Количество: {quantity} штук\n"
        f"🔹 Сумма заказа: {total_price}$\n\n"
        "Почти все готово, осталось оплатить заказ, выбери ниже способ пополнения ✔️"
    )
    
    keyboard = [
        [InlineKeyboardButton("💎 CryptoBot", callback_data='pay_cryptobot')],
        [InlineKeyboardButton("Вернуться назад", callback_data='back_to_buy_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        text=order_text,
        reply_markup=reply_markup,
        parse_mode='HTML'
    )


async def handle_cryptobot_payment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    
    try:
        await query.answer()
    except Exception:
        pass

    order = context.user_data.get('order')
    if not order:
        await query.edit_message_text("Произошла ошибка, пожалуйста, начните заново.", parse_mode='HTML')
        return

    order_id = generate_order_id()
    quantity = order['quantity']
    total_price = order['total_price']
    
    context.user_data['order_id'] = order_id
    
    try:
        invoice_data = await create_crypto_invoice(
            amount=total_price,
            description=f"Stripe Accounts x{quantity}",
            payload=order_id
        )
        
        invoice_id = invoice_data.get('invoice_id')
        context.user_data['invoice_id'] = invoice_id
        context.user_data['invoice_time'] = datetime.now()
        
        payment_url = invoice_data.get('pay_url') or f"https://t.me/CryptoBot?start=IV{invoice_id}"
        
        cryptobot_text = (
            "Шаг 2 из 3... Оплата товара\n\n"
            "Решил использовать CryptoBot? Нет проблем, перепроверь информацию ниже ⬇️\n"
            f"🔹 ID заказа: {order_id}\n"
            "🔹 Товар: Stripe Accounts\n"
            f"🔹 Количество: {quantity} штук\n"
            f"🔹 Сумма заказа: {total_price} USDT\n\n"
            "Все верно? Внизу тебя ждет счет, после его оплаты жми кнопку проверить оплату ⏭️\n\n"
            "⏰ <b>Важно!</b> Счет действителен 5 минут!"
        )

        keyboard = [
            [InlineKeyboardButton("💳 Оплатить счет", url=payment_url)],
            [InlineKeyboardButton("🔄 Проверить оплату", callback_data='check_payment')],
            [InlineKeyboardButton("◀️ Вернуться назад", callback_data='back_to_buy_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        try:
            message = await query.edit_message_text(
                text=cryptobot_text,
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
            context.user_data['payment_message_id'] = message.message_id
            asyncio.create_task(check_invoice_timeout(update, context, invoice_id, message.message_id))
        except Exception:
            message = await query.message.reply_text(
                text=cryptobot_text,
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
            context.user_data['payment_message_id'] = message.message_id
            asyncio.create_task(check_invoice_timeout(update, context, invoice_id, message.message_id))
        
    except Exception as e:
        error_text = (
            f"❌ Произошла ошибка при создании счета.\n"
            f"Ошибка: {str(e)}\n"
            "Попробуйте снова или обратитесь в поддержку."
        )
        keyboard = [
            [InlineKeyboardButton("🔄 Попробовать снова", callback_data='pay_cryptobot')],
            [InlineKeyboardButton("◀️ Вернуться назад", callback_data='back_to_buy_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        try:
            await query.edit_message_text(
                text=error_text,
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
        except Exception:
            await query.message.reply_text(
                text=error_text,
                reply_markup=reply_markup,
                parse_mode='HTML'
            )


async def check_payment_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    invoice_id = context.user_data.get('invoice_id')
    order_id = context.user_data.get('order_id')
    order = context.user_data.get('order')
    invoice_time = context.user_data.get('invoice_time')
    payment_message_id = context.user_data.get('payment_message_id')
    
    if not invoice_id or not order_id or not order or not invoice_time or not payment_message_id:
        try:
            await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=payment_message_id)
        except Exception:
            pass
        await query.message.reply_text(
            "❌ Данные о платеже не найдены. Начните процесс оплаты заново.",
            parse_mode='HTML'
        )
        return
    
    try:
        invoice_data = await check_crypto_invoice(invoice_id)
        
        if not invoice_data:
            try:
                await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=payment_message_id)
            except Exception:
                pass
            await query.message.reply_text("❌ Не удалось получить информацию о платеже. Попробуйте позже.", parse_mode='HTML')
            return
        
        status = invoice_data.get('status')
        
        if status == 'paid':
            try:
                await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=payment_message_id)
            except Exception:
                pass
            credentials = generate_credentials(order['quantity'])
            success_text = (
                "✅ Оплата прошла успешно!\n"
                f"📦 Ваш заказ #{order_id}:\n"
                f"🔢 Количество аккаунтов: {order['quantity']} шт.\n"
                f"💰 Сумма: {order['total_price']}$\n\n"
                "Ваши аккаунты:\n"
                f"{credentials}\n\n"
                "❤️ Спасибо за покупку, приятель!"
            )
            
            keyboard = [
                [InlineKeyboardButton("Назад", callback_data='back_to_main_menu')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.message.reply_text(
                text=success_text,
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
        elif status == 'cancelled':
            try:
                await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=payment_message_id)
            except Exception:
                pass
            await query.message.reply_text("❌ Платеж был отменен!", parse_mode='HTML')
        elif status == 'error':
            try:
                await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=payment_message_id)
            except Exception:
                pass
            await query.message.reply_text("❌ Ошибка при проверке платежа.", parse_mode='HTML')
        elif status == 'not_found':
            try:
                await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=payment_message_id)
            except Exception:
                pass
            await query.message.reply_text("❌ Платеж не найден.", parse_mode='HTML')
        else:
            await query.message.reply_text("⏳ Оплата не сделана, попробуйте ещё раз!", parse_mode='HTML')
            
    except Exception:
        try:
            await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=payment_message_id)
        except Exception:
            pass
        await query.message.reply_text("❌ Произошла внутренняя ошибка.", parse_mode='HTML')


async def support_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    support_text = (
        "🆘 <b>Техническая поддержка</b>\n\n"
        "Есть вопросы? Мы всегда готовы помочь!\n\n"
        "📧 Способы связи:\n"
        "• Telegram: @Xvcen_Garant_BOT\n"
        "• Email: Xvcen@Garant.com\n\n"
        "⏰ Время работы: 24/7\n"
        "⚡ Среднее время ответа: 5-15 минут\n\n"
        "🔸 Часто задаваемые вопросы найдете в разделе FAQ"
    )
    
    keyboard = [
        [InlineKeyboardButton("◀️ Назад", callback_data='back_to_main_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text=support_text,
        reply_markup=reply_markup,
        parse_mode='HTML'
    )


async def faq_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    faq_text = (
        "❓ <b>Часто задаваемые вопросы</b>\n\n"
        "<b>Q:</b> Как долго действительны аккаунты?\n"
        "<b>A:</b> Все аккаунты проверены и готовы к работе длительное время.\n\n"
        "<b>Q:</b> Есть ли гарантия возврата?\n"
        "<b>A:</b> Да, мы гарантируем возврат в случае невалидности.\n\n"
        "<b>Q:</b> Какие способы оплаты доступны?\n"
        "<b>A:</b> Мы принимаем оплату через CryptoBot (USDT, BTC, ETH и др.).\n\n"
        "<b>Q:</b> Сколько времени занимает доставка?\n"
        "<b>A:</b> Мгновенно после оплаты.\n\n"
        "<b>Q:</b> Можно ли купить больше 100 аккаунтов?\n"
        "<b>A:</b> Да, обратитесь в поддержку для индивидуального предложения."
    )
    
    keyboard = [
        [InlineKeyboardButton("◀️ Назад", callback_data='back_to_main_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text=faq_text,
        reply_markup=reply_markup,
        parse_mode='HTML'
    )


async def earn_money_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    earn_text = (
        "💰 <b>Способы заработка</b>\n\n"
        "1️⃣ <b>Реферальная программа</b>\n"
        "• Приглашай друзей и получай 5% с каждой покупки\n"
        "• Пассивный доход без ограничений\n\n"
        "2️⃣ <b>Партнерская программа</b>\n"
        "• Для активных пользователей\n"
        "• Индивидуальные условия\n"
        "• Обращайтесь в поддержку\n\n"
        "3️⃣ <b>Оптовые закупки</b>\n"
        "• Покупай оптом - продавай в розницу\n"
        "• Специальные цены от 100+ аккаунтов\n\n"
        "💡 <b>Начни зарабатывать уже сегодня!</b>"
    )
    
    keyboard = [
        [InlineKeyboardButton("👥 Реферальная система", callback_data='referral_system')],
        [InlineKeyboardButton("◀️ Назад", callback_data='back_to_main_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text=earn_text,
        reply_markup=reply_markup,
        parse_mode='HTML'
    )


async def back_to_buy_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await buy_accounts_handler(update, context)


async def back_to_main_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    
    try:
        await query.answer()
    except Exception:
        pass
    
    welcome_text, reply_markup = get_main_menu_data()

    try:
        await query.edit_message_text(
            text=welcome_text,
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
    except Exception:
        await query.message.reply_text(
            text=welcome_text,
            reply_markup=reply_markup,
            parse_mode='HTML'
        )


def main() -> None:
    application = Application.builder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    
    application.add_handler(CallbackQueryHandler(buy_accounts_handler, pattern='^buy_accounts$'))
    application.add_handler(CallbackQueryHandler(support_handler, pattern='^support$'))
    application.add_handler(CallbackQueryHandler(faq_handler, pattern='^faq$'))
    application.add_handler(CallbackQueryHandler(referral_system_handler, pattern='^referral_system$'))
    application.add_handler(CallbackQueryHandler(earn_money_handler, pattern='^earn_money$'))
    
    application.add_handler(CallbackQueryHandler(handle_pack_selection, pattern=re.compile(r'^\{"action": "select_pack".*')))
    application.add_handler(CallbackQueryHandler(handle_cryptobot_payment, pattern='^pay_cryptobot$'))
    application.add_handler(CallbackQueryHandler(check_payment_handler, pattern='^check_payment$'))
    
    application.add_handler(CallbackQueryHandler(back_to_buy_menu_handler, pattern='^back_to_buy_menu$'))
    application.add_handler(CallbackQueryHandler(back_to_main_menu_handler, pattern='^back_to_main_menu$'))
    
    if WEBHOOK_URL:
        application.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=BOT_TOKEN,
            webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}"
        )
    else:
        application.run_polling()


if __name__ == '__main__':
    main()