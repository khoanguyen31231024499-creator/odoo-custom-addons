# Odoo Custom Phân hệ Purchase cho Cửa hàng thời trang FootGearH



**Môn học:** ERP Mã nguồn mở

**Thông tin thành viên nhóm D**

| Họ và tên | MSSV | Tỷ lệ đóng góp |
| --- | --- | --- |
| Nguyễn Nhật Khoa (trưởng nhóm) | 31231024499 | 100% |
| Trần Thanh Thảo Ly | 31231023750 | 100% |
| Đỗ Nhật Khanh | 31231025385 | 100% |
| Nguyễn Thành Đạt | 31231027610 | 100% |
| Trương Minh Khiêm | 31231026790 | 100% |

---

### Giới thiệu

Bộ module Odoo tùy chỉnh dành riêng cho quy trình quản lý mua hàng (Procure-to-Pay) của cửa hàng thời trang FootGearH. Repository này bao gồm các cấu hình và module mở rộng phục vụ cho việc quản lý Master Data (sản phẩm biến thể theo size, màu sắc), tự động hóa Yêu cầu báo giá (RFQ) theo tồn kho, thiết lập luồng phê duyệt đơn mua hàng (PO) đa cấp, quản lý nhận hàng/tồn đọng (Backorder) và đối soát kế toán 3 bước (Three-Way Matching).

---

### Danh sách Module

| Module | Chức năng | Phụ thuộc chính |
| --- | --- | --- |
| `auto_rfq_reorder`<br> | Tự động quét tồn kho và tạo RFQ nháp khi sản phẩm chạm mức tồn thiểu. Hỗ trợ kích hoạt tức thì hoặc định kỳ, tự động gộp đơn thông minh theo nhà cung cấp và ưu tiên dựa trên thời gian giao hàng (Lead Time).

 | `stock`, `purchase`, `sale`, `point_of_sale`<br> |
| `purchase_user_link`<br> | Quản lý luồng duyệt PO đa cấp. Tự động chặn và chuyển trạng thái "Chờ duyệt" đối với các đơn mua hàng có tổng giá trị từ 20.000.000 VNĐ trở lên. Yêu cầu quản lý phê duyệt hoặc bắt buộc nhập lý do nếu từ chối.

 | `purchase`, `base`<br> |

---

### Quy trình hoạt động chính

* **Thiết lập Master Data:** Khai báo thông tin đơn vị tính, thuộc tính (màu sắc, size), sản phẩm thời trang, danh sách nhà cung cấp và bảng giá nhà cung cấp tương ứng.


* **Cấu hình tái đặt hàng:** Thiết lập mức tồn kho tối thiểu (Min) và tối đa (Max) cho từng biến thể sản phẩm (SKU) thông qua tính năng Reordering Rules.


* **Tự động tạo báo giá (RFQ):** Khi phát sinh giao dịch bán hàng (POS/Sales) hoặc xuất kho khiến tồn kho khả dụng giảm dưới mức Min, hệ thống tự động tạo RFQ nháp. Nếu nhiều sản phẩm cùng thuộc một nhà cung cấp, hệ thống ưu tiên gộp chung vào một chứng từ duy nhất.


* **Xác nhận và Phê duyệt đơn mua (PO):**
* Nhân viên mua hàng kiểm tra RFQ và nhấn xác nhận.


* Nếu tổng giá trị đơn hàng < 20 triệu VNĐ, hệ thống tự động chuyển thành Đơn mua hàng (Purchase Order).


* Nếu tổng giá trị >= 20 triệu VNĐ, luồng dữ liệu bị chặn lại và chuyển sang trạng thái "Chờ duyệt". Quản lý cửa hàng tiến hành đánh giá để phê duyệt hoặc từ chối (bắt buộc lưu vết lý do).




* **Tiếp nhận hàng hóa:** Thủ kho xử lý Phiếu nhập kho (Receipt). Nếu nhà cung cấp giao thiếu hàng so với PO, hệ thống hiển thị tùy chọn tạo phiếu hàng tồn đọng (Backorder) cho số lượng chưa giao.


* **Ghi nhận Hóa đơn & Đối soát:** Kế toán tạo Hóa đơn nhà cung cấp (Vendor Bill) từ PO. Hệ thống tự động thực hiện đối soát 3 bước (Three-Way Matching) giữa Đơn mua hàng, Phiếu nhập kho thực tế và Hóa đơn để phát hiện sai lệch trước khi thanh toán.



---

### Cài đặt

1. Clone repository này vào thư mục custom add-ons của Odoo.
```bash
./odoo-bin --addons-path=/path/to/odoo/addons,/path/to/odoo-custom-addons

```



```
2.  Khởi động lại Odoo server.
3.  Bật chế độ **Developer Mode**.
4.  Truy cập vào **Apps** → Chọn **Update Apps List**.
5.  Tìm kiếm tên module và tiến hành cài đặt.
```
