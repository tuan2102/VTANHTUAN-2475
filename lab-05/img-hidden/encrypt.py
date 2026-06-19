import sys
import os
from PIL import Image

def encode_image(image_path, message):
    # Nếu file không tồn tại ở đường dẫn truyền vào, thử tìm trong cùng thư mục với script này
    if not os.path.exists(image_path):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        alternative_path = os.path.join(script_dir, os.path.basename(image_path))
        if os.path.exists(alternative_path):
            image_path = alternative_path

    img = Image.open(image_path)
    width, height = img.size
    pixel_index = 0
    binary_message = ''.join(format (ord(char), '08b') for char in message)
    binary_message += '00000000' # Đánh dấu kết thúc thông điệp (null byte)

    data_index = 0
    for row in range (height):
        for col in range (width):
            pixel = list(img.getpixel ((col, row)))

            for color_channel in range (3): 
                if data_index < len (binary_message): 
                    pixel [color_channel]  = int (format(pixel[color_channel],'08b') [:-1] + binary_message [data_index], 2)
                    data_index += 1
                    
            img.putpixel ((col, row), tuple (pixel))
            
            if data_index >= len(binary_message):
                break

    script_dir = os.path.dirname(os.path.abspath(__file__))
    encoded_image_path = os.path.join(script_dir, 'encoded_image.png')
    img.save(encoded_image_path)
    print("Steganography complete. Encoded image saved as", encoded_image_path)
    
def main():
    if len(sys.argv) != 3:
        print("Usage: python encrypt.py <image_path> <message>")
        return

    image_path = sys.argv[1] 
    message = sys.argv[2]
    encode_image(image_path, message)

if __name__ == "__main__":
    main()