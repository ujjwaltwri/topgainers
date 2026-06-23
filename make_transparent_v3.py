from PIL import Image

def crisp_background_removal(img_path, out_path):
    img = Image.open(img_path).convert("RGBA")
    gray = img.convert("L")
    
    datas = img.getdata()
    gray_datas = gray.getdata()
    
    new_data = []
    for i, item in enumerate(datas):
        brightness = gray_datas[i]
        
        # Eliminate all shadows and bright backgrounds completely
        if brightness > 150:
            new_data.append((255, 255, 255, 0))
        elif brightness < 60:
            # Fully opaque for the actual indigo ink
            new_data.append((item[0], item[1], item[2], 255))
        else:
            # Tight anti-aliasing blend between 60 and 150
            alpha = int(255 * (150 - brightness) / 90)
            new_data.append((item[0], item[1], item[2], alpha))
            
    img.putdata(new_data)
    
    bbox = img.getbbox()
    if bbox:
        img = img.crop(bbox)
        
    img.save(out_path, "PNG")

img_in = "/Users/ujjwaltiwari/.gemini/antigravity/brain/0302f450-ff36-43e3-81cd-e41a58fe37a5/topgainers_minimalist_1782244306784.png"
img_out = "/Users/ujjwaltiwari/Desktop/topgainers/frontend/images/logo.png"

crisp_background_removal(img_in, img_out)
print("Done!")
