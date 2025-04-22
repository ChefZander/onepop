import random, string, hashlib
from datetime import datetime
import time

import random
import string
import io
from flask import Flask, send_file, request, make_response
from PIL import Image, ImageDraw, ImageFont
import uuid, json

def timestamp():
    return int(time.time())

def generate_short_code():
    """
    Random 5 Letter String with all Letters and Numbers.
    """
    return ''.join(random.choices(string.ascii_letters + string.digits, k=5))
def generate_long_code():
    """
    Random 16 Letter String with all Letters and Numbers.
    """
    return ''.join(random.choices(string.ascii_letters + string.digits, k=16))
def generate_uuid():
    return str(uuid.uuid4())

def hash(input_string): # double sha256
    input_string += "dont_tell_nobody_about_the_onepop_salt"
    input_bytes = input_string.encode('utf-8')
    first_hash = hashlib.sha256(input_bytes).digest()
    second_hash = hashlib.sha256(first_hash).hexdigest()
    return second_hash

def check_pow(captcha_token, nonce, difficulty=14):
    challenge = "popcap-" + captcha_token + "-popcap-" + nonce + "-popcap"
    completed = hashlib.sha256(challenge.encode('utf-8')).hexdigest()
    return (completed.count('0') >= difficulty, completed)

def time_ago(timestamp):
    """
    Convert a timestamp to a human-readable format like "x seconds/minutes/hours/days/weeks/months/years ago"
    Args:
    timestamp: timestamp in seconds since the epoch (output of time.time())
    Returns: A string representing the time difference in human-readable format
    """
    now = datetime.now()
    diff = now - datetime.fromtimestamp(timestamp)

    second_diff = diff.seconds
    day_diff = diff.days

    if day_diff < 0:
        return ''

    if day_diff == 0:
        if second_diff < 10:
            return "just now"
        if second_diff < 60:
            return str(second_diff) + " seconds ago"
        if second_diff < 120:
            return "a minute ago"
        if second_diff < 3600:
            return str(second_diff // 60) + " minutes ago"
        if second_diff < 7200:
            return "an hour ago"
        if second_diff < 86400:
            return str(second_diff // 3600) + " hours ago"
    if day_diff == 1:
        return "yesterday"
    if day_diff < 7:
        return str(day_diff) + " days ago"
    if day_diff < 31:
        return str(day_diff // 7) + " weeks ago"
    if day_diff < 365:
        return str(day_diff // 30) + " months ago"
    return str(day_diff // 365) + " years ago"

def create_captcha_image(text):
    font = ImageFont.load_default(size=30)

    img_width = 100 + random.randrange(-10, 20)
    img_height = 40 + random.randrange(-4, 8)
    background_color = (255, 255, 255) 
    text_color = (0, 0, 0)       

    img = Image.new('RGB', (img_width, img_height), color = background_color)
    d = ImageDraw.Draw(img)

    bbox = d.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    x = ((img_width - text_width) / 2) + random.randrange(-3, 3)
    y = ((img_height - text_height) / 2 - 5) + random.randrange(-3, 3)

    d.text((x, y), text, fill=text_color, font=font)

    pixels = img.load()
    width, height = img.size

    noise_factor = 150
    for i in range(width):
        for j in range(height):
            if pixels[i, j] == (0, 0, 0):
                random_color = (random.randint(0, noise_factor), random.randint(0, noise_factor), random.randint(0, noise_factor))
                pixels[i, j] = random_color
            else:
                random_color = (255 - random.randint(0, noise_factor), 255 - random.randint(0, noise_factor), 255 - random.randint(0, noise_factor))
                pixels[i, j] = random_color

    for _ in range(15):
        x1 = random.randint(0, img_width)
        y1 = random.randint(0, img_height)
        d.circle((x1, y1), radius=2, fill=(random.randint(0,200), random.randint(0,200), random.randint(0,200)))

    byte_arr = io.BytesIO()
    img.save(byte_arr, format='PNG')
    byte_arr.seek(0)

    return byte_arr