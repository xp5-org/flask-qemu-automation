from PIL import Image
import numpy as np
import os

def find_button_in_screenshot(button_path, screenshot_path):
    # load both images as grayscale
    full_img = Image.open(screenshot_path).convert("L")
    button_img = Image.open(button_path).convert("L")

    # optional: save converted images for inspection
    full_converted_path = os.path.splitext(screenshot_path)[0] + "_converted.png"
    button_converted_path = os.path.splitext(button_path)[0] + "_converted.png"
    full_img.save(full_converted_path)
    button_img.save(button_converted_path)

    # convert to arrays
    full_arr = np.array(full_img, dtype=np.uint8)
    button_arr = np.array(button_img, dtype=np.uint8)

    fh, fw = full_arr.shape
    bh, bw = button_arr.shape

    # slide button over full image 1 pixel at a time
    for y in range(fh - bh + 1):
        for x in range(fw - bw + 1):
            patch = full_arr[y:y+bh, x:x+bw]
            if (patch == button_arr).all():  # exact match
                return True, (x, y), full_converted_path, button_converted_path

    return False, "Button not found", full_converted_path, button_converted_path


if __name__ == "__main__":
    button_path = "/app/buttontest/inactive_titlebar_system7.png"
    screenshot_path = "/app/buttontest/image.png"

    found, pos, full_conv, btn_conv = find_button_in_screenshot(button_path, screenshot_path)
    print("Full converted saved at:", full_conv)
    print("Button converted saved at:", btn_conv)
    if found:
        print("Button found at:", pos)
    else:
        print(pos)
