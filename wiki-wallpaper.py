#!/usr/bin/env python3
"""
Wikipedia Wallpaper of the Day for Mac

This script:
1. Downloads the Wikipedia Picture of the Day
2. Gets the description of the image
3. Creates a new wallpaper with the image and description
4. Sets the new image as the desktop wallpaper on macOS
"""

import os
import sys
import requests
from datetime import datetime
import subprocess
import tempfile
from PIL import Image, ImageDraw, ImageFont
from bs4 import BeautifulSoup
import textwrap
import io
import re

def get_wikipedia_potd():
    """Fetch Wikipedia's Picture of the Day and its description."""
    
    # Get the Wikipedia Picture of the Day page
    url = "https://en.wikipedia.org/wiki/Wikipedia:Picture_of_the_day"
    response = requests.get(url)
    if response.status_code != 200:
        print(f"Error: Failed to fetch Wikipedia page. Status code: {response.status_code}")
        sys.exit(1)
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Find the image and description
    potd_div = soup.find('div', id='potd')
    if not potd_div:
        print("Error: Could not find Picture of the Day on Wikipedia")
        sys.exit(1)
    
    # Get the image URL
    img_tag = potd_div.find('img')
    if not img_tag or 'src' not in img_tag.attrs:
        print("Error: Could not find the image in the Picture of the Day")
        sys.exit(1)
    
    img_src = img_tag['src']
    if not img_src.startswith('http'):
        img_src = "https:" + img_src
    
    # Get a higher resolution version by manipulating the URL
    # Wikipedia thumbnail URLs contain /thumb/ and end with /XXXpx-filename
    if '/thumb/' in img_src:
        img_src = re.sub(r'/thumb/', '/', img_src)
        img_src = re.sub(r'/\d+px-', '/', img_src)
    
    # Get the description
    description_div = soup.find('div', id='potd-desc') or soup.find('div', id='potd-description')
    if not description_div:
        print("Error: Could not find the description for the Picture of the Day")
        sys.exit(1)
    
    description = description_div.get_text().strip()
    
    return img_src, description

def download_image(url):
    """Download the image from the URL."""
    response = requests.get(url)
    if response.status_code != 200:
        print(f"Error: Failed to download image. Status code: {response.status_code}")
        sys.exit(1)
    
    return Image.open(io.BytesIO(response.content))

def create_wallpaper(image, description):
    """Create a wallpaper with the image and description."""
    
    # Get the screen resolution
    screen_size = get_screen_size()
    
    # Create a new image with the screen resolution
    wallpaper = Image.new('RGB', screen_size, color='black')
    
    # Calculate the sizes
    desc_height = int(screen_size[1] * 0.15)  # 15% of the height for the description
    img_height = screen_size[1] - desc_height
    
    # Resize the image maintaining aspect ratio
    img_aspect = image.width / image.height
    img_width = int(img_height * img_aspect)
    
    if img_width > screen_size[0]:
        # If the image is too wide, scale it down
        img_width = screen_size[0]
        img_height = int(img_width / img_aspect)
    
    resized_img = image.resize((img_width, img_height), Image.LANCZOS)
    
    # Calculate position to center the image
    img_pos_x = (screen_size[0] - img_width) // 2
    img_pos_y = 0
    
    # Paste the image
    wallpaper.paste(resized_img, (img_pos_x, img_pos_y))
    
    # Add the description
    draw = ImageDraw.Draw(wallpaper)
    
    # Try to find a suitable font
    font_size = 20
    font_path = "/System/Library/Fonts/Supplemental/Arial.ttf"  # Default font path for macOS
    
    # Try different system fonts if the default isn't available
    if not os.path.exists(font_path):
        font_paths = [
            "/System/Library/Fonts/Helvetica.ttc",
            "/Library/Fonts/Arial.ttf",
            "/System/Library/Fonts/Supplemental/Courier New.ttf"
        ]
        for path in font_paths:
            if os.path.exists(path):
                font_path = path
                break
    
    try:
        font = ImageFont.truetype(font_path, font_size)
    except IOError:
        # Fall back to default font if TrueType font is not available
        font = ImageFont.load_default()
    
    # Wrap text to fit the screen width
    max_width = screen_size[0] - 40  # 20px padding on each side
    wrapped_text = textwrap.fill(description, width=int(max_width / (font_size * 0.6)))
    
    # Draw the description text
    text_color = (255, 255, 255)  # White text
    text_position = (20, img_height + 20)  # 20px padding from the top of the description area
    
    draw.text(text_position, wrapped_text, fill=text_color, font=font)
    
    return wallpaper

def get_screen_size():
    """Get the screen resolution of the primary display."""
    try:
        result = subprocess.run(['system_profiler', 'SPDisplaysDataType'], capture_output=True, text=True)
        output = result.stdout
        
        # Parse the output to find the resolution
        resolution_pattern = r'Resolution: (\d+) x (\d+)'
        match = re.search(resolution_pattern, output)
        
        if match:
            width = int(match.group(1))
            height = int(match.group(2))
            return (width, height)
    except Exception as e:
        print(f"Error getting screen size: {e}")
    
    # Fall back to a common resolution if we can't detect it
    return (1920, 1080)

def set_desktop_wallpaper(image_path):
    """Set the desktop wallpaper on macOS."""
    try:
        script = f'''
        tell application "System Events"
            set desktop picture to POSIX file "{image_path}"
        end tell
        '''
        subprocess.run(['osascript', '-e', script], check=True)
        print(f"Wallpaper set successfully to {image_path}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error setting wallpaper: {e}")
        return False

def main():
    print("Fetching Wikipedia Picture of the Day...")
    img_url, description = get_wikipedia_potd()
    
    print("Downloading image...")
    image = download_image(img_url)
    
    print("Creating wallpaper with description...")
    wallpaper = create_wallpaper(image, description)
    
    # Save the wallpaper to a temporary file
    temp_dir = tempfile.gettempdir()
    today = datetime.now().strftime("%Y-%m-%d")
    wallpaper_path = os.path.join(temp_dir, f"wikipedia_potd_{today}.jpg")
    
    wallpaper.save(wallpaper_path, "JPEG", quality=95)
    print(f"Wallpaper saved to {wallpaper_path}")
    
    print("Setting as desktop wallpaper...")
    success = set_desktop_wallpaper(wallpaper_path)
    
    if success:
        print("Done! Wikipedia Picture of the Day set as your desktop wallpaper.")
    else:
        print("Failed to set the wallpaper. You can manually set it from:", wallpaper_path)

if __name__ == "__main__":
    main()
