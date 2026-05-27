import cv2

print("OpenCV版本:", cv2.__version__)
print("\n正在检测USB摄像头...")

# 检测前5个摄像头索引
for index in range(5):
    cap = cv2.VideoCapture(index)
    if cap.isOpened():
        ret, frame = cap.read()
        if ret:
            height, width = frame.shape[:2]
            print(f"✅ 摄像头索引 {index}: 已打开 - 分辨率 {width}x{height}")
            cap.release()
        else:
            print(f"⚠️ 摄像头索引 {index}: 已打开但无法读取帧")
            cap.release()
    else:
        print(f"❌ 摄像头索引 {index}: 未找到")

print("\n检测完成！")
