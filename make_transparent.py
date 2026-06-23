from PIL import Image

def make_transparent(img_path, out_path):
    img = Image.open(img_path).convert("RGBA")
    datas = img.getdata()
    
    new_data = []
    for item in datas:
        # Change all white (also shades of white) to transparent
        # The logo is indigo on white, so we'll check if R, G, B are high
        if item[0] > 240 and item[1] > 240 and item[2] > 240:
            new_data.append((255, 255, 255, 0))
        else:
            new_data.append(item)
            
    img.putdata(new_data)
    img.save(out_path, "PNG")

img_in = "/Users/ujjwaltiwari/.gemini/antigravity/brain/0302f450-ff36-43e3-81cd-e41a58fe37a5/topgainers_minimalist_1782244306784.png"
img_out = "/Users/ujjwaltiwari/Desktop/topgainers/frontend/images/logo.png"

import os
os.makedirs("/Users/ujjwaltiwari/Desktop/topgainers/frontend/images", exist_ok=True)

make_transparent(img_in, img_out)
print("Done!")
