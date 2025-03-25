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
import time

def get_wikipedia_potd():
    """Fetch Wikipedia's Picture of the Day and its description."""
    
    # Get the Wikipedia main page where the POTD is displayed
    url = "https://en.wikipedia.org/wiki/Main_Page"
    response = requests.get(url)
    if response.status_code != 200:
        print(f"Error: Failed to fetch Wikipedia main page. Status code: {response.status_code}")
        sys.exit(1)
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Find the image and description in the main page
    # The Picture of the Day is typically in a div with id='mp-tfp'
    potd_div = soup.find('div', id='mp-tfp')
    if not potd_div:
        # Try alternative method - look for the POTD heading and get the following div
        potd_heading = soup.find('h2', id='mp-tfa-h2')
        if potd_heading and potd_heading.find(string=lambda text: 'picture of the day' in text.lower() if text else False):
            potd_div = potd_heading.find_next('div')
    
    if not potd_div:
        # Try another approach - look for text in headings that might indicate POTD
        for heading in soup.find_all(['h2', 'h3']):
            heading_text = heading.get_text().lower()
            if 'picture of the day' in heading_text or "today's featured picture" in heading_text:
                potd_div = heading.find_next('div')
                break
    
    if not potd_div:
        # If all else fails, we'll try the archive page
        print("Could not find POTD on main page, trying the archive...")
        return get_wikipedia_potd_from_archive()
    
    # Get the image URL
    img_tag = potd_div.find('img')
    if not img_tag or 'src' not in img_tag.attrs:
        print("Error: Could not find the image in the Picture of the Day")
        # Try the archive as fallback
        return get_wikipedia_potd_from_archive()
    
    img_src = img_tag['src']
    if not img_src.startswith('http'):
        img_src = "https:" + img_src
    
    # Get a higher resolution version by manipulating the URL
    # Wikipedia thumbnail URLs contain /thumb/ and end with /XXXpx-filename
    if '/thumb/' in img_src:
        img_src = re.sub(r'/thumb/', '/', img_src)
        #img_src = re.sub(r'/\d+px-', '/', img_src)
    
    # Get the description
    # On the main page, the description is usually in a div near the image
    description = ""
    if potd_div:
        # First, try to find the caption which may be in a div or directly in the potd_div
        caption_div = potd_div.find('div', class_='description') or potd_div.find('div', class_='center')
        if caption_div:
            description = caption_div.get_text().strip()
        else:
            # If no specific caption div, extract all text from the potd_div except link text
            for element in potd_div.find_all(string=True):
                parent = element.parent
                if parent.name != 'a' and element.strip():
                    description += element.strip() + " "
            description = description.strip()
    
    if not description:
        # If we couldn't find a description, try to get the alt text of the image
        if img_tag and 'alt' in img_tag.attrs:
            description = img_tag['alt'].strip()
    
    # If we still don't have a description, use a default one
    if not description:
        description = "Wikipedia Picture of the Day"
    
    return img_src, description

def get_wikipedia_potd_from_archive():
    """Fetch Wikipedia's Picture of the Day from the archive as a fallback."""
    
    # Get today's date formatted as needed
    today = datetime.now()
    date_str = today.strftime("%Y-%m-%d")
    
    # Try to get the POTD from the "On the main pages" page
    url = "https://en.wikipedia.org/wiki/Wikipedia:Picture_of_the_day/On_the_main_pages"
    response = requests.get(url)
    if response.status_code != 200:
        print(f"Error: Failed to fetch Wikipedia archive page. Status code: {response.status_code}")
        sys.exit(1)
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Look for today's date on the page
    for heading in soup.find_all(['h2', 'h3', 'h4']):
        heading_text = heading.get_text().strip().lower()
        if 'today' in heading_text or date_str in heading_text:
            section = heading.find_next('div')
            if section:
                img_tag = section.find('img')
                if img_tag and 'src' in img_tag.attrs:
                    img_src = img_tag['src']
                    if not img_src.startswith('http'):
                        img_src = "https:" + img_src
                    
                    # Get higher resolution version
                    if '/thumb/' in img_src:
                        img_src = re.sub(r'/thumb/', '/', img_src)
                        img_src = re.sub(r'/\d+px-', '/', img_src)
                    
                    # Try to find description
                    description = ""
                    caption_div = section.find('div', class_='description') or section.find('div', class_='center')
                    if caption_div:
                        description = caption_div.get_text().strip()
                    else:
                        # Extract all text from the section except link text
                        for element in section.find_all(string=True):
                            if element.parent.name != 'a' and element.strip():
                                description += element.strip() + " "
                        description = description.strip()
                    
                    if not description and img_tag.get('alt'):
                        description = img_tag['alt'].strip()
                    
                    if not description:
                        description = "Wikipedia Picture of the Day"
                    
                    return img_src, description
    
    # If all else fails, use the Commons POTD as a last resort
    print("Could not find POTD in archives, trying Wikimedia Commons...")
    return get_commons_potd()

def get_commons_potd():
    """Fetch Wikimedia Commons' Picture of the Day as a last resort."""
    
    url = "https://commons.wikimedia.org/wiki/Commons:Picture_of_the_day"
    response = requests.get(url)
    if response.status_code != 200:
        print("Error: Failed to fetch Commons POTD. Using a default image.")
        # Return a default Wikipedia image as the absolute last resort
        return "https://upload.wikimedia.org/wikipedia/commons/thumb/8/80/Wikipedia-logo-v2.svg/1200px-Wikipedia-logo-v2.svg.png", "Wikimedia Commons Picture of the Day could not be retrieved. This is the Wikipedia logo as a fallback."
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Try to find the main POTD container
    potd_div = soup.find('div', id='potd')
    if not potd_div:
        # Look for any div that might contain the POTD
        for div in soup.find_all('div', class_='main-box'):
            if div.find('img'):
                potd_div = div
                break
    
    if not potd_div or not potd_div.find('img'):
        print("Error: Could not find an image in Commons POTD. Using a default image.")
        return "https://upload.wikimedia.org/wikipedia/commons/thumb/8/80/Wikipedia-logo-v2.svg/1200px-Wikipedia-logo-v2.svg.png", "Wikimedia Commons Picture of the Day could not be retrieved. This is the Wikipedia logo as a fallback."
    
    img_tag = potd_div.find('img')
    img_src = img_tag['src']
    if not img_src.startswith('http'):
        img_src = "https:" + img_src
    
    # Get higher resolution
    if '/thumb/' in img_src:
        img_src = re.sub(r'/thumb/', '/', img_src)
        img_src = re.sub(r'/\d+px-', '/', img_src)
    
    # Try to get description
    description = ""
    caption_div = soup.find('div', id='potd-description') or soup.find('div', class_='description')
    if caption_div:
        description = caption_div.get_text().strip()
    else:
        # If no description found, use image alt text or a default
        if img_tag.get('alt'):
            description = img_tag['alt'].strip()
        else:
            description = "Wikimedia Commons Picture of the Day"
    
    return img_src, description

def download_image(url):
    """Download the image from the URL with retry capability."""
    max_retries = 3
    retry_delay = 2  # seconds
    
    for attempt in range(max_retries):
        try:
            # Set a user agent to avoid blocking
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code != 200:
                print(f"Attempt {attempt+1}/{max_retries}: Failed to download image. Status code: {response.status_code}")
                if attempt < max_retries - 1:
                    print(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    continue
                else:
                    print("All download attempts failed. Using default image.")
                    # Return a default image as fallback
                    default_img_url = "https://upload.wikimedia.org/wikipedia/commons/thumb/8/80/Wikipedia-logo-v2.svg/1200px-Wikipedia-logo-v2.svg.png"
                    default_response = requests.get(default_img_url, headers=headers)
                    return Image.open(io.BytesIO(default_response.content))
            
            # Try to open the image content
            try:
                return Image.open(io.BytesIO(response.content))
            except Exception as e:
                print(f"Attempt {attempt+1}/{max_retries}: Error opening image: {e}")
                if attempt < max_retries - 1:
                    print(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    print("Failed to open image after all attempts. Using default image.")
                    default_img_url = "https://upload.wikimedia.org/wikipedia/commons/thumb/8/80/Wikipedia-logo-v2.svg/1200px-Wikipedia-logo-v2.svg.png"
                    default_response = requests.get(default_img_url, headers=headers)
                    return Image.open(io.BytesIO(default_response.content))
                
        except Exception as e:
            print(f"Attempt {attempt+1}/{max_retries}: Error downloading image: {e}")
            if attempt < max_retries - 1:
                print(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                print("All download attempts failed. Using default image.")
                # Return a default image as fallback
                try:
                    default_img_url = "https://upload.wikimedia.org/wikipedia/commons/thumb/8/80/Wikipedia-logo-v2.svg/1200px-Wikipedia-logo-v2.svg.png"
                    default_response = requests.get(default_img_url, headers=headers)
                    return Image.open(io.BytesIO(default_response.content))
                except Exception as fallback_error:
                    print(f"Even the fallback image failed to load: {fallback_error}")
                    # Create a simple blank image as an absolute last resort
                    blank_img = Image.new('RGB', (800, 600), color='white')
                    draw = ImageDraw.Draw(blank_img)
                    try:
                        font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 20)
                    except:
                        font = ImageFont.load_default()
                    draw.text((50, 50), "Failed to download Wikipedia Picture of the Day", fill='black', font=font)
                    return blank_img

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
    try:
        print("Fetching Wikipedia Picture of the Day...")
        img_url, description = get_wikipedia_potd()
        print(f"Image URL: {img_url}")
        print(f"Description: {description[:100]}..." if len(description) > 100 else f"Description: {description}")
        
        try:
            print("Downloading image...")
            image = download_image(img_url)
            print(f"Image dimensions: {image.width}x{image.height}")
            
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
        except Exception as e:
            print(f"Error processing the image: {e}")
            print("Full error details:", sys.exc_info())
    except Exception as e:
        print(f"Error in main function: {e}")
        print("Full error details:", sys.exc_info())

if __name__ == "__main__":
    main()
