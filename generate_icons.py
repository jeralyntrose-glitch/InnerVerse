#!/usr/bin/env python3
"""
Generate PWA icons for InnerVerse
Creates teal brain logo icons in all required sizes
"""

from PIL import Image, ImageDraw, ImageFont
import os

# Icon sizes needed
SIZES = [72, 96, 128, 144, 152, 192, 384, 512]
MASKABLE_SIZES = [192, 512]

# Colors
TEAL = (16, 163, 127)  # #10A37F
WHITE = (255, 255, 255)

def create_brain_icon(size, is_maskable=False):
    """Create a minimalist brain icon"""
    # Create image with teal background
    img = Image.new('RGB', (size, size), TEAL)
    draw = ImageDraw.Draw(img)
    
    # Calculate safe zone for maskable icons (80% center)
    if is_maskable:
        safe_margin = size * 0.1  # 10% margin on each side
    else:
        safe_margin = size * 0.05  # 5% margin for regular icons
    
    # Draw brain shape (simplified as circles and curves)
    center_x = size // 2
    center_y = size // 2
    brain_radius = (size - safe_margin * 2) // 2
    
    # Main brain circle (white outline)
    draw.ellipse(
        [center_x - brain_radius, center_y - brain_radius, 
         center_x + brain_radius, center_y + brain_radius],
        outline=WHITE,
        width=max(2, size // 80)
    )
    
    # Left hemisphere curve
    left_curve_x = center_x - brain_radius // 3
    draw.arc(
        [left_curve_x - brain_radius // 2, center_y - brain_radius // 2,
         left_curve_x + brain_radius // 2, center_y + brain_radius // 2],
        start=90, end=270,
        fill=WHITE,
        width=max(2, size // 100)
    )
    
    # Right hemisphere curve
    right_curve_x = center_x + brain_radius // 3
    draw.arc(
        [right_curve_x - brain_radius // 2, center_y - brain_radius // 2,
         right_curve_x + brain_radius // 2, center_y + brain_radius // 2],
        start=270, end=90,
        fill=WHITE,
        width=max(2, size // 100)
    )
    
    # Draw "IV" text in center (InnerVerse initials)
    try:
        # Try to use a nice font, fall back to default
        font_size = size // 4
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
    except:
        font = ImageFont.load_default()
    
    text = "IV"
    # Get text bounding box
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    text_x = center_x - text_width // 2
    text_y = center_y - text_height // 2
    
    # Draw text shadow for depth
    shadow_offset = max(1, size // 200)
    draw.text((text_x + shadow_offset, text_y + shadow_offset), text, fill=(0, 0, 0, 50), font=font)
    
    # Draw main text
    draw.text((text_x, text_y), text, fill=WHITE, font=font)
    
    return img

def main():
    print("🎨 Generating InnerVerse PWA icons...")
    
    # Create regular icons
    for size in SIZES:
        print(f"  📱 Creating {size}x{size} icon...")
        icon = create_brain_icon(size, is_maskable=False)
        icon.save(f"icons/icon-{size}x{size}.png", "PNG")
    
    # Create maskable icons
    for size in MASKABLE_SIZES:
        print(f"  🎭 Creating {size}x{size} maskable icon...")
        icon = create_brain_icon(size, is_maskable=True)
        icon.save(f"icons/icon-maskable-{size}x{size}.png", "PNG")
    
    print("✅ All icons generated successfully!")
    print(f"📁 Icons saved to /icons/ directory")

if __name__ == "__main__":
    main()
