import os
import telebot
from PIL import Image, ImageOps
import io
from telebot import types
from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv())

bot = telebot.TeleBot(token=os.getenv('TOKEN'))

user_states = {}  # тут будем хранить информацию о действиях пользователя

# набор символов из которых составляем изображение
ASCII_CHARS = '@%#*+=-:. '


def resize_image(image, new_width=100):
    width, height = image.size
    ratio = height / width
    new_height = int(new_width * ratio)
    return image.resize((new_width, new_height))


def grayify(image):
    return image.convert("L")


def image_to_ascii(image_stream, new_width=40):
    # Переводим в оттенки серого
    image = Image.open(image_stream).convert('L')

    # меняем размер сохраняя отношение сторон
    width, height = image.size
    aspect_ratio = height / float(width)
    new_height = int(
        aspect_ratio * new_width * 0.55)  # 0,55 так как буквы выше чем шире
    img_resized = image.resize((new_width, new_height))

    img_str = pixels_to_ascii(img_resized)
    img_width = img_resized.width

    max_characters = 4000 - (new_width + 1)
    max_rows = max_characters // (new_width + 1)

    ascii_art = ""
    for i in range(0, min(max_rows * img_width, len(img_str)), img_width):
        ascii_art += img_str[i:i + img_width] + "\n"

    return ascii_art


def pixels_to_ascii(image):
    pixels = image.getdata()
    characters = ""
    for pixel in pixels:
        characters += ASCII_CHARS[pixel * len(ASCII_CHARS) // 256]
    return characters


# Огрубляем изображение
def pixelate_image(image, pixel_size):
    image = image.resize(
        (image.size[0] // pixel_size, image.size[1] // pixel_size),
        Image.NEAREST
    )
    image = image.resize(
        (image.size[0] * pixel_size, image.size[1] * pixel_size),
        Image.NEAREST
    )
    return image


@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "Send me an image, and I'll provide options for you!")


@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    bot.reply_to(message, "I got your photo! Please choose what you'd like to do with it.",
                 reply_markup=get_options_keyboard())
    user_states[message.chat.id] = {'photo': message.photo[-1].file_id}


def get_options_keyboard():
    keyboard = types.InlineKeyboardMarkup()
    pixelate_btn = types.InlineKeyboardButton("Pixelate", callback_data="pixelate")
    ascii_btn = types.InlineKeyboardButton("ASCII Art", callback_data="ascii")
    inv_btn = types.InlineKeyboardButton('Inversion', callback_data='inversion')
    keyboard.add(pixelate_btn, ascii_btn, inv_btn)
    return keyboard



@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    if call.data == "pixelate":
        bot.answer_callback_query(call.id, "Pixelating your image...")
        pixelate_and_send(call.message)
    elif call.data == "ascii":
        '''
        При нажатии кнопки ASCII Art выводится сообщение с предложением пользователю
        ввести свой набор символов или воспользоваться набором по умолчанию.
        '''
        message = call.message
        bot.send_message(message.chat.id, 'Введите набор символов для создания ASCII-арта или "0" для загрузки набора символов по умолчанию')
        '''
        При нажатии кнопки Inversion цвета изображения меняются на противоположные
        '''
    elif call.data == "inversion":
        bot.answer_callback_query(call.id, 'Inversion...')
        invert_colors(call.message)

@bot.message_handler(content_types=['text'])
def choice_asсii(message: types.Message):
    '''
    Функция переопределяет переменную ASCII_CHARS в соответствии с установками пользователя
    и вызывает метод для преобразования изображения в ASCII-арт.
    '''
    global ASCII_CHARS
    if message.text != '0':
        ASCII_CHARS = message.text
    else:
        message.text = ASCII_CHARS
    ascii_and_send(message)

def pixelate_and_send(message):
    photo_id = user_states[message.chat.id]['photo']
    file_info = bot.get_file(photo_id)
    downloaded_file = bot.download_file(file_info.file_path)

    image_stream = io.BytesIO(downloaded_file)
    image = Image.open(image_stream)
    pixelated = pixelate_image(image, 20)

    output_stream = io.BytesIO()
    pixelated.save(output_stream, format="JPEG")
    output_stream.seek(0)
    bot.send_photo(message.chat.id, output_stream)


def ascii_and_send(message):
    photo_id = user_states[message.chat.id]['photo']
    file_info = bot.get_file(photo_id)
    downloaded_file = bot.download_file(file_info.file_path)

    image_stream = io.BytesIO(downloaded_file)
    ascii_art = image_to_ascii(image_stream)
    bot.send_message(message.chat.id, f"```\n{ascii_art}\n```", parse_mode="MarkdownV2")

def get_bot(message):
    bot.send_message(message.chat.id, f'Введите символы для создания ASCII-арта')

def invert_colors(message):
    '''
    Функция преобразует изображение изменяя цвета на противоположные - т.н. инверсия изображения
    '''
    photo_id = user_states[message.chat.id]['photo']
    file_info = bot.get_file(photo_id)
    downloaded_file = bot.download_file(file_info.file_path)
    image_stream = io.BytesIO(downloaded_file)
    image = Image.open(image_stream)
    inverted_image = ImageOps.invert(image)
    bot.send_photo(message.chat.id, inverted_image)



bot.polling(none_stop=True)
