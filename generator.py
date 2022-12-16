import random
from PIL import Image, ImageDraw

# 创建 10x10 的图片，填充为白色
width, height = 10, 10
image = Image.new('RGB', (width*20, height*20), (255, 255, 255))
draw = ImageDraw.Draw(image)

# 生成随机数字，并将它们写入图片
for x in range(width):
    for y in range(height):
        num = random.randint(0, 99)
        draw.text((x*20+5, y*20+5), str(num), fill=(0, 0, 0))

# 绘制表格的线条
for x in range(width+1):
    draw.line((x*20, 0, x*20, height*20), fill=(0, 0, 0))
for y in range(height+1):
    draw.line((0, y*20, width*20, y*20), fill=(0, 0, 0))

# 保存图片
image.save('table.png')
