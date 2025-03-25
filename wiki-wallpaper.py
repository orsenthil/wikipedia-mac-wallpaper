#!/usr/bin/env python3
"""
Wikipedia Wallpaper of the Day for Mac

This script:
1. Downloads the Wikipedia Picture of the Day using MediaWiki API
2. Gets the description of the image
3. Creates a new wallpaper with the image and description
4. Sets the new image as the desktop wallpaper on macOS
"""

import os
import sys
import requests
from datetime import date
import subprocess
import tempfile
from PIL import Image, ImageDraw, ImageFont
from bs4 import BeautifulSoup
import textwrap
import io
import re
import time

# Set up a session for API requests
SESSION = requests.Session()
ENDPOINT = "https://en.wikipedia.org/w/api.php"

def fetch_potd(current_date=None):
    """
    Returns image data related to the current POTD using MediaWiki API
    """
    if current_date is None:
        current_date = date.today()

    date_iso = current_date.isoformat()
    title = "Template:POTD protected/" + date_iso

    # First API call to get the image filename
    params = {
        "action": "query",
        "format": "json",
        "formatversion": "2",
        "prop": "images",
        "titles": title
    }

    try:
        response = SESSION.get(url=ENDPOINT, params=params)
        data = response.json()
        
        # Check if we got valid data
        if "query" not in data or "pages" not in data["query"] or not data["query"]["pages"]:
            print(f"Error: Invalid API response for date {date_iso}")
            return None, None
            
        # Get the filename from the response
        if "images" not in data["query"]["pages"][0] or not data["query"]["pages"][0]["images"]:
            print(f"Error: No images found for date {date_iso}")
            return None, None
            
        filename = data["query"]["pages"][0]["images"][0]["title"]
        
        # Second API call to get the image URL
        image_url = fetch_image_src(filename)
        
        # Third API call to get the description
        description = fetch_image_description(date_iso)
        
        print(f"Successfully found POTD: {filename}")
        
        return image_url, description
        
    except Exception as e:
        print(f"Error fetching POTD: {e}")
        return None, None

def fetch_image_src(filename):
    """
    Returns the POTD's image url
    """
    params = {
        "action": "query",
        "format": "json",
        "prop": "imageinfo",
        "iiprop": "url",
        "titles": filename
    }

    try:
        response = SESSION.get(url=ENDPOINT, params=params)
        data = response.json()
        
        # Navigate through the response to get the URL
        page = next(iter(data["query"]["pages"].values()))
        if "imageinfo" not in page or not page["imageinfo"]:
            print(f"Error: No image info found for {filename}")
            return None
            
        image_info = page["imageinfo"][0]
        image_url = image_info["url"]
        
        return image_url
        
    except Exception as e:
        print(f"Error fetching image URL: {e}")
        return None

def fetch_image_description(date_iso):
    """
    Get the description for the POTD
    """
    # Get the description from the template page
    params = {
        "action": "parse",
        "format": "json",
        "page": f"Template:POTD protected/{date_iso}",
        "prop": "text"
    }
    
    try:
        response = SESSION.get(url=ENDPOINT, params=params)
        data = response.json()
        
        if "parse" not in data or "text" not in data["parse"]:
            print("Error: Could not parse description page")
            return "Wikipedia Picture of the Day"
            
        html_content = data["parse"]["text"]["*"]
        
        # Parse the HTML to extract the description
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Try to find the description in different possible locations
        description = ""
        
        # Method 1: Look for div with class 'description'
        desc_div = soup.find('div', class_='description')
        if desc_div:
            description = desc_div.get_text().strip()
        
        # Method 2: Look for the text after the image
        if not description:
            # Find all paragraphs
            paragraphs = soup.find_all('p')
            if paragraphs:
                # Take the longest paragraph as it's likely the description
                description = max(paragraphs, key=lambda p: len(p.get_text())).get_text().strip()
        
        # Method 3: Just grab all the text
        if not description:
            description = soup.get_text().strip()
            
        # Clean up the description
        description = re.sub(r'\s+', ' ', description)  # Replace multiple spaces with single space
        
        if not description:
            description = "Wikipedia Picture of the Day"
        
        return description
        
    except Exception as e:
        print(f"Error fetching description: {e}")
        return "Wikipedia Picture of the Day"

def download_image(url):
    """Download the image from the URL with retry capability."""
    if not url:
        print("Error: No URL provided")
        return create_fallback_image()
        
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
                    return create_fallback_image()
            
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
                    return create_fallback_image()
                
        except Exception as e:
            print(f"Attempt {attempt+1}/{max_retries}: Error downloading image: {e}")
            if attempt < max_retries - 1:
                print(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                print("All download attempts failed. Using default image.")
                return create_fallback_image()

def create_fallback_image():
    """Create a fallback image when download fails"""
    try:
        # Try to download the Wikipedia logo as a fallback
        default_img_url = "https://upload.wikimedia.org/wikipedia/commons/thumb/8/80/Wikipedia-logo-v2.svg/1200px-Wikipedia-logo-v2.svg.png"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36'
        }
        default_response = requests.get(default_img_url, headers=headers)
        return Image.open(io.BytesIO(default_response.content))
    except Exception:
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
    """Set the desktop wallpaper on all displays on macOS."""
    try:
        # This script sets the wallpaper on all displays
        script = f'''
        tell application "System Events"
            set desktopCount to count of desktops
            repeat with desktopNumber from 1 to desktopCount
                tell desktop desktopNumber
                    set picture to "{image_path}"
                end tell
            end repeat
        end tell
        '''
        
        result = subprocess.run(['osascript', '-e', script], 
                               capture_output=True, 
                               text=True,
                               check=False)
        
        if result.returncode == 0:
            print(f"Wallpaper set successfully on all displays: {image_path}")
            return True
        else:
            print(f"System Events method failed: {result.stderr}")
            
            # Try the Finder method as a fallback
            finder_script = f'''
            tell application "Finder"
                set desktop picture to POSIX file "{image_path}"
            end tell
            '''
            
            finder_result = subprocess.run(['osascript', '-e', finder_script], 
                                         capture_output=True, 
                                         text=True)
                                         
            if finder_result.returncode == 0:
                print(f"Wallpaper set using Finder method (primary display only): {image_path}")
                return True
            else:
                print(f"Finder method also failed: {finder_result.stderr}")
    except Exception as e:
        print(f"Error setting wallpaper: {e}")
    
    print(f"\nAutomated methods failed. The wallpaper is saved at: {image_path}")
    print("You can manually set it as your wallpaper by right-clicking the file and selecting 'Set Desktop Picture'")
    return False

def main():
    try:
        print("Fetching Wikipedia Picture of the Day using API...")
        img_url, description = fetch_potd()
        
        if not img_url:
            print("Failed to get the Picture of the Day. Using fallback image.")
            image = create_fallback_image()
            description = "Wikipedia Picture of the Day could not be retrieved."
        else:
            print(f"Image URL: {img_url}")
            print(f"Description: {description[:100]}..." if len(description) > 100 else f"Description: {description}")
            
            print("Downloading image...")
            image = download_image(img_url)
        
        print(f"Image dimensions: {image.width}x{image.height}")
        
        print("Creating wallpaper with description...")
        wallpaper = create_wallpaper(image, description)
        
        # Save the wallpaper to a temporary file
        temp_dir = tempfile.gettempdir()
        today = date.today().strftime("%Y-%m-%d")
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
        print(f"Error in main function: {e}")
        print("Full error details:", sys.exc_info())

if __name__ == "__main__":
    main()
