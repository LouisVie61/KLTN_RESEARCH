## Pipeline: From Smart Contract --> Symbolic Execution: do automation test

    Solidity (.sol)
        ↓
    Solc Compiler
        ↓
    EVM Bytecode + ABI (Ethereum Virtual Machine)
        ↓
    Disassembly (Bytecode → Opcode)
        ↓
    Control Flow Graph (CFG)
        ↓
    Symbolic Execution Engine (Interpreter) - Main
        ↓
    Path Conditions (PC)
        ↓
    SMT Solver (Z3)
        ↓
    Concrete Inputs / Bug Detection

### Research:

1. From Smart Contract (contract.sol) --> ByteCode + ABI:

    AST (Abstract Syntax Tree): trong quá trình compile: thì src code được chia thành các đoạn nhỏ được gọi là token thông qua Lexical Analysis hay còn được gọi là token hóa (Tokenization)
    Do các được chia thành các token và phải tuân theo một thứ tự từ src code => Chúng được truyền vào một cấu trúc dữ liệu: TREE

    => Do đó AST: là một bộ phần trừu tượng hóa đi thông tin và chỉ giữ lại lượng thông tin đủ dùng để giúp Compiler hiểu src code.

    Cấu trúc của Contract:
    - State variables: biến trạng thái: đại diện cho state đắt đỏ nhất
    - Functions: Entry points
    - Events: các ràng buộc và cơ chế ghi log

    Quan tầm đến AST vì nó giữ được semantic cao hơn so với bytecode - nơi các liên kết bị xóa nhòa

    ABI: Application Binary Interface: một cuốn từ điển giúp cho Symbolic Engine biết được cần gọi hàm nào với tham số đầu vào là kiểu giữ liệu gì: Không thử input bừa bãi --> Phải dùng kiểu ABI định nghĩa

    EVM Bytecode: "Mã thực thi" - 2 phần chính: 
    - Creation/ Init Bytecode: được khởi tạo khi lần đầu chạy contract
    - Runtime Bytecode: đối tượng chính cho Symbolic Execution, phần thực sự nằm trên Blockchain: mô hình gồm số Hex đại diện cho mã Opcodes

2. Analysis: Runtime Bytecode --> Opcode
- Properties:
    - Immutable
    - Stack-based: LIFO
    - Low-level: Opcodes represented by hexadecimal byte values

- Process Meaning: Bước này giúp ta chuyển từ một chuỗi số vô hồn sang một danh sách các chỉ thị mà con người và máy tính có thể hiểu được logic.

- Ví dụ:

```bash
6001600055

60 01 --> PUSH 0x01  --> Đẩy giá trị 1 vào stack
60 00 --> PUSH 0x00  --> Đẩy giá trị 0 vào stack
55 --> SSTORE --> Lưu giá trị ở Stack[1] vào vị trí của Stack[0] trong storage (storage[0] = 1)

```
3. Opcode - based for building CFG
- Disassembly không làm bytecode chạy khác đi; nó chỉ chuyển hex sang opcode để ta nhận diện các điểm rẽ nhánh JUMP/JUMPI và dựng CFG phục vụ symbolic execution.
- CFG - Control flow graph
    - Nodes: basic block: - một cụm opcodes chạy liên tục mà không có lệnh nhảy
    - Edges: Thể hiện luồng đi giữa các block

4. Symbolic Execution:

- Properties:
    - Symbolic State Tracking:
        - Symbolic Stack: chưa các biểu thức toán học: ADD, SUB, ...
        - Symbolic Memory & Storage (M, Stor): bản đồ ánh xạ từ địa chỉ sang các biểu thức ký hiệu
        - Path Condition (PC): Thành phần quan trọng nhất: tập hợp tích lũy các ràng buộc toán học để đi tới node đó

    - Workflow:
        - Stage 1: Từ ROOT của CFG: các input đầu vào được khởi tạo dưới các dạng ký hiệu tự do (x_data, y_val).
        - Stage 2: Tree Traversal - Duyệt node: trong một basic block các thì SE sẽ thực hiện tuần tự các opcode
            - Arithmetic Command: biến thành biểu thức thay vì giá trị
            - Updating Command: ghi lại rằng giá trị của vị trí A bây giờ là biểu thức V
        - Stage 3: Xử lý các lệnh rẽ nhánh
            - 3.1: Lấy điều kiện nhảy: giả sử là biểu thức C
            - 3.2: Tạo 2 thế giới song song: 
                - Nhánh true: Tạo một bản sao của nhánh hiện tại: PC_true = PC ∧ C
                - Nhánh false: Tạo một bản sao khác: PC_false = PC ∧ ¬C
            - 3.3: Satisfiability Check: kiểm tra tính khả thi: gửi PC sang SMT Solver Z3
                - return UNSAT: đường cụt --> Không bao giờ xảy ra --> Prune
                - return SAT: tiếp tục đào sâu hơn vào các node tiếp theo trên CFG
        - Stage 4: Phát hiện lỗi: tại mỗi node, sẽ được đối chiếu với các template nhận diện lỗi:
            - Ví dụ: Integer Overflow: nếu thực hiện ADD mà Z3 phát hiện > 2^256 - 1 trong phạm vi PC hiện tại --> Báo lỗi
            - Ví dụ: Reentrancy Nếu gặp lệnh CALL mà Storage chưa cập nhật xong --> Báo lỗi
