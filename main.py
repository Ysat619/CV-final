import cv2
import numpy as np
import pytesseract
import os
from prettytable import PrettyTable

# pylint: disable=no-member,pointless-string-statement


# 读取所有图片，返回文件路径列表
def read_images_filename():
    # 获取当前工作目录
    current_dir = os.getcwd()

    result_list = []

    # 枚举./images目录中的文件
    for file in os.listdir(current_dir + '/images'):
        # 如果文件是图片文件，则打印文件名
        if file.endswith('.jpg') or file.endswith('.png') or file.endswith('.bmp'):
            result_list.append(current_dir + '/images/' + file)
    return result_list


def identify_table(image):
    # 灰度图片
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    """
    自适应阈值算法(adaptiveThreshold): 灰度图像->二值图像
    ~gray: 灰度图像的反色图像
    cv2.ADAPTIVE_THRESH_GAUSSIAN_C: 使用高斯平滑算法进行自适应阈值计算。
    cv2.THRESH_BINARY:使用二值化，即将像素值大于阈值的像素赋值为 255, 将像素值小于等于阈值的像素赋值为 0。
    35: 自适应阈值计算的块大小。块大小越大，自适应阈值计算的精度就越低，但噪声对结果的影响就越小
    -5: 调整阈值时使用的常数。调整阈值时, 可以使用这个常数来调整阈值的大小。
    """
    binary = cv2.adaptiveThreshold(
        ~gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 35, -5)

    """
    【识别表格的横线】【识别表格的竖线】

    使用了形态学操作来处理二值图像。形态学操作是图像处理中常用的一种方法，可以用来对图像进行腐蚀、膨胀、开运算和闭运算等操作。
    【腐蚀操作】可以【去除】图像中的【噪点】，【膨胀操作】则可以【填补】图像中的【空洞】。

    cv2.getStructuringElement()
    生成一个【矩形结构元素】。这个结构元素是形态学操作的核心，它决定了形态学操作对图像的影响范围。

    cv2.erode()
    对二值图像进行腐蚀操作。
    函数接受三个参数：输入图像、结构元素和迭代次数。
        输入图像是之前处理过的二值图像
        结构元素是刚刚生成的【矩形结构元素】
        迭代次数设为 1

    cv2.dilate() 函数来对腐蚀后的图像进行膨胀操作，函数的参数设置和 cv2.erode() 函数类似，
    都是使用腐蚀后的图像、矩形结构元素和迭代次数为 1

    通过腐蚀和膨胀的操作，可以使图像中的文字更加清晰，并去除噪点。这在文字识别过程中非常有用，可以提升识别准确率。
    """
    # 识别横线
    rows, cols = binary.shape
    scale = 40
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (cols // scale, 1))
    eroded = cv2.erode(binary, kernel, iterations=1)
    dilatedcol = cv2.dilate(eroded, kernel, iterations=1)
    # 识别竖线
    scale = 20
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, rows // scale))
    eroded = cv2.erode(binary, kernel, iterations=1)
    dilatedrow = cv2.dilate(eroded, kernel, iterations=1)

    # 标识交点（按位与运算将两个二值图像进行合并）
    bitwiseAnd = cv2.bitwise_and(dilatedcol, dilatedrow)

    # 标识表格
    merge = cv2.add(dilatedcol, dilatedrow)
    # cv2.imshow("表格整体展示：", merge)

    # 两张图片进行减法运算，去掉表格框线
    merge2 = cv2.subtract(binary, merge)
    # cv2.imshow("图片去掉表格框线展示：", merge2)

    # 识别黑白图中的白色交叉点，将横纵坐标取出
    ys, xs = np.where(bitwiseAnd > 0)

    mylisty = []  # 纵坐标
    mylistx = []  # 横坐标

    # 通过排序，获取跳变的x和y的值，说明是交点，否则交点会有好多像素值值相近，我只取相近值的最后一点
    # 这个10的跳变不是固定的，根据不同的图片会有微调，基本上为单元格表格的高度（y坐标跳变）和长度（x坐标跳变）
    i = 0
    myxs = np.sort(xs)
    for i in range(len(myxs) - 1):
        if (myxs[i + 1] - myxs[i] > 10):
            mylistx.append(myxs[i])
        i = i + 1
    mylistx.append(myxs[i])  # 要将最后一个点加入

    i = 0
    myys = np.sort(ys)
    # print(np.sort(ys))
    for i in range(len(myys) - 1):
        if (myys[i + 1] - myys[i] > 10):
            mylisty.append(myys[i])
        i = i + 1
    mylisty.append(myys[i])  # 要将最后一个点加入

    # 定义要过滤的特殊字符
    special_char_list = ['|', '/', ';',
                         '}', ' ', '{', '\n', '-', '»', '(', ')']

    # 识别后的结果数组
    result_list = []

    # 循环y坐标，x坐标分割表格
    for i in range(len(mylisty) - 1):
        table_row = []
        for j in range(len(mylistx) - 1):
            # 在分割时，第一个参数为y坐标，第二个参数为x坐标
            ROI = image[mylisty[i] + 3:mylisty[i + 1] - 3,
                        mylistx[j]:mylistx[j + 1] - 3]  # 减去3的原因是由于我缩小ROI范围

            # 预处理图像，以提高识别精度
            ROI = cv2.cvtColor(ROI, cv2.COLOR_BGR2GRAY)
            ROI = cv2.threshold(
                ROI, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]

            # 识别文字
            text = pytesseract.image_to_string(
                ROI, lang="eng", config="--psm 7")
            text = text.strip()  # 去掉前后空白字符

            # 过滤掉特殊字符
            text = ''.join(
                [char for char in text if char not in special_char_list])
            if text == '':
                continue
            if text[0] == '.':
                text = text[1:]
            
            table_row.append(text)
        result_list.append(table_row)
    return result_list


# 打印表格
def pretty_print(lst):
    table = PrettyTable()
    table.field_names = lst[0]
    table.add_rows(lst[1:])
    print(table)


if __name__ == "__main__":
    images_name = read_images_filename()
    print(images_name)
    for filename in images_name:
        img = cv2.imread(filename, 1)
        res = identify_table(img)
        print(filename)
        pretty_print(res)
