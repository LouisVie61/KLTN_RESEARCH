## Description: Hệ thống tự động kiểm thử an ninh cho Smart Contract bằng Symbolic Execution
## Basic features:
	Upload file (Solidity code)

	Show: CFG

	Report:

	Project Management

	Slither/ Mythril integration

	Web UI manipulation
    
	Role-based Access Control (RBAC)

	Scanning history

## Advanced features compared to market
	Formal Specification: cho phép người dùng viết các thuộc bằng toán học mà contract phải tuân thủ
	
	"Symbolic Execution" Engine: Thay vì chạy test case (chạy balance = 100, balance = 10, …), hệ thống dùng biến giả (symbols: ex: x, y, …) để duyệt qua mọi nhánh thực thi khả thi của code

	Model Checking Integration: Kiểm chứng xem trạng thái của contract có bao giờ rơi vào vùng "nguy hiểm" không; hay có thể hiểu: Duyệt toàn bộ trạng thái có thể của hệ thống để kiểm tra xem có trạng thái nào vi phạm điều kiện an toàn không.

	Automated Counter-example: Nếu có lỗi, hệ thống chỉ ra chính xác một chuỗi giao dịch dẫn đến lỗi đó; Tức là không chỉ nói bị bug gì, ở đâu mà chỉ ra thêm các giao dịch nào bị lỗi; một execution trace hợp lệ dẫn tới trạng thái vi phạm.

    Gas Optimization Verification: Chứng minh toán học rằng một hàm đã được tối ưu hóa về mặt lưu trữ dữ liệu; thường mọi người đo (benchmark) thì mình đi prove bằng toán học;

## Nhiệm vụ thầy giao:
    Thực hiện research về: Symbolic Execution trên một smart contract
