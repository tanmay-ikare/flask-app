from PIL import Image,ImageDraw,ImageFont


def create_id(name, designation, phone_number, email, address):
    image = Image.open("id_template.png")
    d= ImageDraw.Draw(image)
    
    def add_text(text,text_pos,font_size):
        font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf",font_size)
        d.text(text_pos,text,font=font,fill="black")

    add_text(name,(158,535),45)
    add_text(designation,(265,585),30)
    add_text(phone_number,(90,700),30)
    add_text(email,(90,782),30)
    add_text(address,(90,882),30)
    
    
    passport_image = Image.open("passport_photo.jpg").convert("RGBA")
    passport_image = passport_image.resize((350, 350))  # optional
    
    image.paste(passport_image, (130, 150), passport_image)
    image.save(f"output.png")
    
    
create_id("Tanmay Ikare","SDET","8855922810","ikare.tanmay@gmail.com","barshi, Maharashtra")