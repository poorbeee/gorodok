from PIL import Image
import os

# Ищем исходник
source = None
for name in ['icon-source.png', 'icon-source.jpg', 'icon-source.jpeg']:
    if os.path.exists(name):
        source = name
        break

if not source:
    print("❌ Не найден icon-source.png или icon-source.jpg в папке")
    print("   Положи картинку рядом со скриптом и назови её icon-source.png")
    exit(1)

print(f"Использую: {source}")

img = Image.open(source).convert('RGBA')
w, h = img.size
print(f"Размер исходника: {w}x{h}")

# Обрезаем до квадрата по центру
side = min(w, h)
left = (w - side) // 2
top = (h - side) // 2
img = img.crop((left, top, left + side, top + side))

# Делаем скруглённые углы (для красивой иконки на Android)
def rounded(img, radius_ratio=0.2):
    size = img.size[0]
    radius = int(size * radius_ratio)
    mask = Image.new('L', (size, size), 0)
    from PIL import ImageDraw
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle([(0, 0), (size, size)], radius=radius, fill=255)
    result = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    result.paste(img, (0, 0), mask)
    return result

rounded_img = rounded(img, 0.2)

# Сохраняем в разных размерах
for size, name in [(512, 'icon-512.png'), (192, 'icon-192.png'), (180, 'apple-touch-icon.png'), (32, 'favicon-32.png')]:
    rounded_img.resize((size, size), Image.LANCZOS).save(name, 'PNG')
    print(f"✅ {name} ({size}x{size})")

print("\n🎉 Готово! Иконки созданы в папке проекта.")