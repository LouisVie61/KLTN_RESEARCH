## Luồng:

SC (file .sol) -> EVM compiler -> Bytecode + ABI -> Disassembly -> CFG -> Symbolic Execution -> Z3 SMT Provers -> Bug detection

## Research

1. AST: abstract syntax tree: đoạn code .sol được trunk tuần tự thành token bởi lexical analysis (tokenization: token hóa)
-> AST: trừu tượng hóa đi một phần thông tin của .sol nhưng vẫn giữ được sematic để Compiler hiểu source code; 

2. Bytecode + ABI
- ABI: application binary interface: đóng vai trò như một cuốn từ điển, hoặc map giúp cho symbolic execution không bị lạc, cho biết tham số với kiểu dữ liệu của nó.
- Bytecode:
    - 2 thành phần:
        - Create bytecode: được tạo ra duy nhất một lần trong lần đầu tiên chạy
        - Runtime bytecode: là một dãy số hexadecimal value: tượng trưng cho Opcode (JUMP, JUMPI, ...)
    - Runtime bytecode: là đối tượng chính của SE; mang tính không thay đổi khi đã deploy, hoạt động theo kiểu stack-based (LIFO)

3. Disassembly: Bytecode -> Opcode
- Bytecode cụ thể là Runtime bytecode được chuyển thành Opcode: từ đây, dev sẽ không cảm thấy bị thẳng tuột từ khi nhìn con số Bytecode vô hồn, mà xuất hiện các lệnh JUMP, JUMPI để rẽ nhánh

4. CFG:
- Khi đã có Opcode -> Việc chuyển sang CFG dễ dàng hơn.
- Properties:
    - Nodes: basic block: các opcode cho đến khi xuất hiện JUMP
    - Edges: các cạnh liên kết để chỉ ra sự tuần tự

5. Symbolic Execution: - Nhân vật chính:
- Thành phần: Symbolic State Tracking
    - Symbolic Stack: chuyển giá trị các biến về: x_data, y_val
    - Symbolic Mem & Storage: anh xa sang bieu thuc ky hieu
    - Path Condition: tap hop tich luy cac rang buoc dan toi node nay
