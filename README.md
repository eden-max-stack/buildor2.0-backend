# buildor2.0-backend

## This Project is under development 🧑‍💻🌐

### Instructions to Follow -

1. Run from repo root directory.
   i.e. **buildor2.0-backend/**

2. RUN THIS COMMAND (ONLY THIS)
   i.e. **uvicorn app.main:app --reload**

3. do not run any .py file directly.

4. CONFIRM API is running-
   Open Browser -> http://127.0.0.1:8000/docs -> You must see:
   **Graph Analysis**
   **POST /api/v1/graph/analyze**

## current implementation

1. layer_1/ is a folder containing code to convert a piece of python code into an AST, a CFG and a DFG.

2. The AST (abstract syntax tree) will give us syntactic information about the code itself. This will answer questions like:
   Is there a conditional statement in the code?
   Which operators being used in a statement.
   Which nested statements exist in the code
   etc.

   ```
   if x + 1 == y:
      z = x * 2
   ```

The AST will tell you that there is an if statement, the condition is a binary condition, that there is an assignment inside the body of the if condition, etc.

3. The CFG (control flow graph) will give us information on which statements run, and in which order.
   Are there unreachable paths?
   How does information flow or get modified through the code written?
   What is the path of execution?

   ```
    if x > 0:
        y = 1
    else:
        y = 2
    print(y)

   ```

The CFG will show you

    ```
    start
    ├── x > 0 ──▶ y = 1 ─┐
    └── else ──▶ y = 2 ──┤
                        ▼
                    print(y)

    ```

4. The DFG (data flow graph) will give us information on how data is being updated throughout the life-cycle of the code.
   Where does the value come from?
   How is it being modified?
   Where is it being used?

   ```total = 0
      for x in arr:
         total += x
      return sum
   ```

   In the code given above, the variable `total` is being updated, `sum` is returned, but never defined.
