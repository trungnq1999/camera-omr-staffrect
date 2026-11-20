# Tiền xử lý v2.2 (phân tích sau khi đã thấy tập kiểm tra Xiaomi)

v2.2 sửa ba lỗi lộ ra trên ảnh Xiaomi 12S Pro. Trên ảnh này trang chỉ chiếm khoảng 25% khung và nằm trên mặt bàn gỗ:
1. **Độ phân giải xử lý:** nếu khoảng dòng kẻ dưới 7 px ở 2000 px, xử lý lại ở độ phân giải cao hơn, tối đa bằng ảnh gốc.
2. **Đoạn khuông phải nằm trên nền giấy:** loại các đoạn có nền màu cam/vàng và đậm màu hơn giấy (vân gỗ). Giấy trong bóng râm hơi xanh vẫn được giữ.
3. **Vùng nhạc:** lấy mọi vùng khuông có diện tích ít nhất 15% vùng lớn nhất, thay vì chỉ lấy vùng lớn nhất.
4. **Ngưỡng lật 180°:** đặt về 0. Ngưỡng −0,2 của v2.1 được chỉnh theo iPhone, nơi ảnh lộn ngược hiếm gặp.

Số ảnh camera "xử lý tốt" (đúng hướng, sai số hình học < 2%, giữ ≥ 97% vùng nhạc), đo bằng `crop_eval.py`:

| | v2.1 | v2.2 |
|---|---|---|
| Xiaomi (160 ảnh, độ phân giải gốc) | 65 | 131 |
| iPhone (160 ảnh, thu nhỏ 2000 px) | 128 | 127 |

Vì v2.2 được chỉnh SAU khi xem ảnh Xiaomi, kết quả Xiaomi của v2.2 là phân tích sau, không phải kiểm tra độc lập. Kiểm tra sạch cho v2.2 cần ảnh từ máy thứ ba.

## Chạy

```bash
cd /mnt/g/doan/minh
unzip -o rectify_v22.zip          # chỉ thêm pp_study/rectify_v22/, không đụng file đã khoá
sha256sum pp_study/rectify_v22/*.py pp_study/rectify_v22/*.npy pp_study/rectify_v22/*.json > frozen/FROZEN_V22.sha256
nohup bash pp_study/rectify_v22/run_v22.sh > run_v22.log 2>&1 &
```
