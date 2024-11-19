import os
import argparse
import cv2
import numpy as np
from plantcv import plantcv as pcv
import matplotlib.pyplot as plt


# Transformation functions
def gaussian_blur(img, channel="b"):
    """Applies Gaussian blur based on specified channel."""
    try:
        if channel in ["l", "a", "b"]:
            a_gray = pcv.rgb2gray_lab(rgb_img=img, channel=channel)
        elif channel in ["h", "s", "v"]:
            a_gray = pcv.rgb2gray_hsv(rgb_img=img, channel=channel)
        elif channel in ["c", "m", "y", "k"]:
            a_gray = pcv.rgb2gray_cmyk(rgb_img=img, channel=channel)
        else:
            raise ValueError("Invalid channel specified.")
        bin_mask = pcv.threshold.otsu(gray_img=a_gray, object_type="light")
        cleaned_mask = pcv.fill_holes(bin_mask)
        return cleaned_mask
    except Exception as e:
        print(f"Error in gaussian_blur: {e}")
        raise


def mask_objects(img, mask):
    return pcv.apply_mask(img=img, mask=mask, mask_color="white")


def remove_black(img):
    gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, mask = cv2.threshold(gray_img, 20, 255, cv2.THRESH_BINARY)
    return pcv.apply_mask(img=img, mask=mask, mask_color="white")


def roi(img, mask):
    roi_image = img.copy()
    roi_image[mask != 0] = (0, 255, 0)
    x, y, w, h = cv2.boundingRect(mask)
    return cv2.rectangle(roi_image, (x, y), (x + w, y + h), (255, 0, 0), 2)


def analyze_object(img, mask):
    return pcv.analyze.size(img=img, labeled_mask=mask)


def create_pseudolandmarks_image(image, mask):
    pseudolandmarks = image.copy()
    top_x, bottom_x, center_v_x = pcv.homology.x_axis_pseudolandmarks(
        img=pseudolandmarks, mask=mask, label='default'
    )
    colors = [(0, 0, 255), (255, 0, 255), (255, 0, 0)]
    for points, color in zip([top_x, bottom_x, center_v_x], colors):
        for point in points:
            center = (point[0][0], point[0][1])
            pseudolandmarks = draw_circle(pseudolandmarks, center, radius=5, color=color)
    return pseudolandmarks


def analyze_color(img, mask, output):
    try:
        pcv.analyze.color(rgb_img=img, labeled_mask=mask, colorspaces='all')
        color_data = pcv.outputs.observations['default_1']
        histograms = {
            channel: color_data[f'{channel}_frequencies']['value']
            for channel in ['hue', 'saturation', 'value', 'lightness', 'blue', 'green', 'red', 'green-magenta', 'blue-yellow']
        }

        plt.figure(figsize=(10, 6))
        for channel, data in histograms.items():
            plt.plot(data, label=channel)
        plt.legend()
        plt.title("Color Channel Histogram")
        plt.xlabel("Pixel Intensity")
        plt.ylabel("Proportion")
        plt.savefig(os.path.join(output, "color_histogram.png"))
        plt.close()
    except Exception as e:
        print(f"Error in analyze_color: {e}")
        raise


def draw_circle(image, center, radius, color):
    x, y = np.ogrid[:image.shape[0], :image.shape[1]]
    mask = (x - center[1]) ** 2 + (y - center[0]) ** 2 <= radius ** 2
    image[mask] = color
    return image

def bayes(img):
    mask = pcv.naive_bayes_classifier(rgb_img=img, pdf_file="./output.txt")
    plant_mask = mask['plant']
    plant_mask = pcv.fill_holes(plant_mask)

    return plant_mask


def process_image(img_path, output_dir, transformation):
    try:
        os.makedirs(output_dir, exist_ok=True)
        img, _, _ = pcv.readimage(filename=img_path)

        if transformation == "gaussian_blur":
            result = gaussian_blur(img)
        elif transformation == "mask_objects":
            mask = gaussian_blur(img)
            result = mask_objects(img, mask)
        elif transformation == "remove_black":
            result = remove_black(img)
        elif transformation == "roi":
            mask = gaussian_blur(img)
            result = roi(img, mask)
        elif transformation == "analyze_object":
            mask = gaussian_blur(img)
            result = analyze_object(img, mask)
        elif transformation == "create_pseudolandmarks":
            mask = gaussian_blur(img)
            result = create_pseudolandmarks_image(img, mask)
        elif transformation == "analyze_color":
            mask = gaussian_blur(img)
            analyze_color(img, mask, output_dir)
            print("Color analysis saved.")
            return
        else:
            raise ValueError("Unsupported transformation selected.")

        pcv.print_image(result, os.path.join(output_dir, f"{transformation}.png"))
        print(f"{transformation} result saved in {output_dir}.")
    except Exception as e:
        print(f"Error processing image: {e}")
        raise


# CLI setup
def main():
    parser = argparse.ArgumentParser(description="Image Transformation Script")
    parser.add_argument("input", help="Path to the input image or directory.")
    parser.add_argument("output", help="Directory to save results.")
    parser.add_argument(
        "--transformation",
        choices=[
            "gaussian_blur",
            "mask_objects",
            "remove_black",
            "roi",
            "analyze_object",
            "create_pseudolandmarks",
            "analyze_color",
        ],
        required=True,
        help="Transformation to apply.",
    )

    args = parser.parse_args()

    if os.path.isfile(args.input):
        process_image(args.input, args.output, args.transformation)
    elif os.path.isdir(args.input):
        for file in os.listdir(args.input):
            if file.lower().endswith(("jpg", "jpeg", "png")):
                process_image(os.path.join(args.input, file), args.output, args.transformation)
    else:
        print("Invalid input path. Provide an image or directory.")


if __name__ == "__main__":
    main()