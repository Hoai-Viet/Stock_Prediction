# Prediction Display Settings

## Quy tắc hiện tại

- Dự đoán BUY/SELL được lấy từ tập luật FP-Growth trong DB.
- Chấp nhận luật có confidence thật `>= 0.60`.
- Nếu confidence thật `< 0.60`, kết quả là `HOLD`.
- Confidence hiển thị trong card `Today's Prediction` được lấy từ confidence thật của luật rồi cộng thêm `0.10` (10 điểm phần trăm).
- Confidence hiển thị tối đa là `100%`.
- Ví dụ: confidence thật `0.6744` được hiển thị thành `77.4%` trên FE.

## Top symbol

- Chỉ card nhỏ bên phải sử dụng thống kê này.
- Không thay đổi bảng dự đoán hôm nay hoặc bảng lịch sử lớn.
- Top symbol dùng lịch sử thật trong 3 tháng gần nhất từ `fact_txn_fp_growth_metrics`.
- Mỗi ngày lịch sử được khớp lại với tập luật FP-Growth trong DB.
- Chỉ tính dự đoán được tạo bởi luật có confidence thật `>= 0.70`.
- Card hiển thị tối đa 5 mã có tỷ lệ thắng `>= 75%` trong cửa sổ 3 tháng gần nhất năm 2026.
- Gộp kết quả BUY và SELL theo từng mã, không chọn riêng hướng có tỷ lệ tốt hơn.
- Chỉ hiển thị mã và tỷ lệ thắng; không hiển thị nhãn BUY/SELL hoặc số đúng/tổng số dự đoán.
- Bên dưới danh sách có khối mời người dùng đăng ký để nhận thêm mã.
- Khối đăng ký là liên kết có thể bấm và mở email tới `support@stockpredictor.vn`.
- Khối đăng ký dùng nút vàng một dòng, kèm icon `frontend/logo/signup.png` sát bên phải nội dung.
- Các dòng top symbol dùng layout compact: chữ `14px`, padding dọc `8px`, khoảng cách giữa dòng `6px`.
- Không hiển thị card tỷ suất sinh lời từ các dự báo đúng ở sidebar.
- Không dùng hai ngày fake và không dùng confidence đã cộng 10%.
- Danh sách demo cố định gồm `OCB`, `EIB`, `HDB`, `PGB`, `VIB`; các mã phải tồn tại trong response lịch sử thật trước khi hiển thị.
- Phần trăm hiển thị trên card là số demo cố định giảm dần: `84.8%`, `81.6%`, `78.4%`, `74.2%`, `70.8%`.
- Các phần trăm demo không phải accuracy lịch sử thật và không được dùng cho tính toán backend.

## Lưu ý về tỷ lệ hiển thị

- Giao diện không hiển thị số mẫu `1/1`, `2/2`.
- Backend vẫn giữ accuracy thật và số mẫu để kiểm tra, đối soát.
- Dải `70% - 85%` trên card chỉ là dữ liệu demo theo setting giao diện, không phản ánh accuracy thật của từng mã.

## Lịch sử

- Giữ nguyên bảng lịch sử 10 ngày hiện có.
- Giữ nguyên 2 ngày fake đang dùng để đưa tỷ lệ lịch sử về khoảng `80%`.
- Dữ liệu lịch sử không được dùng để quyết định top symbol.

## Tóm tắt công thức

```text
Được dự đoán BUY/SELL: real_confidence >= 0.60
Confidence hiển thị: min(real_confidence + 0.10, 1.00)
Được vào top symbol: real_confidence >= 0.70
Tỷ lệ thắng tối thiểu để hiển thị: win_rate >= 75%
```
