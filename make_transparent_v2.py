from PIL import Image

def flawless_background_removal(img_path, out_path):
    img = Image.open(img_path).convert("RGBA")
    gray = img.convert("L")
    
    # Let's find the primary dark color of the logo by sampling the center
    width, height = img.size
    center_color = img.getpixel((width//2, height//2))
    
    datas = img.getdata()
    gray_datas = gray.getdata()
    
    new_data = []
    for i, item in enumerate(datas):
        brightness = gray_datas[i]
        # Calculate alpha: 255 (opaque) for dark pixels, 0 (transparent) for white pixels.
        # We can add a slight contrast curve so off-white becomes perfectly transparent
        alpha = max(0, min(255, int((255 - brightness) * 1.2))) 
        
        if alpha < 10:
            # perfect transparent
            new_data.append((255, 255, 255, 0))
        else:
            # We preserve the original color but apply the new alpha channel for flawless anti-aliasing
            new_data.append((item[0], item[1], item[2], alpha))
            
    img.putdata(new_data)
    
    # We should also crop the image tightly around the visible pixels to remove all the empty space!
    bbox = img.getbbox()
    if bbox:
        img = img.crop(bbox)
        
    img.save(out_path, "PNG")

img_in = "/Users/ujjwaltiwari/.gemini/antigravity/brain/0302f450-ff36-43e3-81cd-e41a58fe37a5/topgainers_minimalist_1782244306784.png"
img_out = "/Users/ujjwaltiwari/Desktop/topgainers/frontend/images/logo.png"

flawless_background_removal(img_in, img_out)
print("Done!")
