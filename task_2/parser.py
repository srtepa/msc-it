import tkinter as tk
from tkinter import scrolledtext, messagebox
import re

def calculate_metrics():
    code = text_area.get("1.0", tk.END).strip()
    if not code:
        messagebox.showwarning("Внимание", "Введите код для анализа!")
        return

    code = re.sub(r'//.*', '', code)
    code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)
    code = re.sub(r'".*?"', '""', code)
    code = re.sub(r"'.*?'", "''", code)
    code = re.sub(r"`.*?`", "``", code, flags=re.DOTALL)

    N = code.count(';') + len(re.findall(r'\b(if|for|while|switch)\b|(?<!\?)\?(?![.:?])', code))
    if N == 0: N = 1 

    CL = len(re.findall(r'\b(if|for|while|case)\b|(?<!\?)\?(?![.:?])', code))

    tokens = re.findall(r'\b(?:if|else|for|while|do|switch|case)\b|(?<!\?)\?(?![.:?])|\{|\}|\(|\)|:|;', code)
    
    stack = []
    switch_cases = []
    current_depth = 0
    max_depth = 0
    
    in_condition_for = None
    paren_depth = 0
    expecting_body_for = None
    current_control = None
    just_popped_do = False

    def get_switch_depth():
        return sum(max(0, c - 1) for c in switch_cases)

    def cascade_pop_single():
        nonlocal current_depth, just_popped_do
        popped_any = False
        while stack and stack[-1][0] == 'SINGLE':
            if just_popped_do: break
            
            _, popped_kw = stack.pop()
            current_depth -= 1
            if popped_kw == 'do':
                just_popped_do = True
                break
            else:
                just_popped_do = False
            popped_any = True
        return popped_any

    for t in tokens:
        if in_condition_for:
            if t == '(': paren_depth += 1
            elif t == ')':
                paren_depth -= 1
                if paren_depth <= 0:
                    paren_depth = 0
                    if in_condition_for != 'do-while':
                        expecting_body_for = 'control' if in_condition_for != 'switch' else 'switch'
                    in_condition_for = None
            continue

        if expecting_body_for:
            if t == '{':
                if expecting_body_for == 'control':
                    stack.append(('BLOCK', current_control))
                    current_depth += 1
                    max_depth = max(max_depth, current_depth + get_switch_depth())
                elif expecting_body_for == 'switch':
                    stack.append(('SWITCH', current_control))
                    switch_cases.append(0)
                expecting_body_for = None
                just_popped_do = False
                continue 
            else:
                if expecting_body_for == 'control':
                    stack.append(('SINGLE', current_control))
                    current_depth += 1
                    max_depth = max(max_depth, current_depth + get_switch_depth())
                expecting_body_for = None

        if t in ['if', 'for', 'switch']:
            just_popped_do = False
            in_condition_for = t
            current_control = t
            paren_depth = 0
        elif t == 'while':
            if just_popped_do:
                just_popped_do = False
                in_condition_for = 'do-while'
            else:
                in_condition_for = t
                current_control = t
            paren_depth = 0
        elif t in ['else', 'do']:
            just_popped_do = False
            expecting_body_for = 'control'
            current_control = t
        elif t == '?':
            just_popped_do = False
            stack.append(('TERNARY', '?'))
            current_depth += 1
            max_depth = max(max_depth, current_depth + get_switch_depth())
        elif t == ':':
            just_popped_do = False
            if stack and stack[-1][0] == 'TERNARY':
                stack.pop()
                current_depth -= 1
        elif t == 'case':
            just_popped_do = False
            if switch_cases:
                switch_cases[-1] += 1
                max_depth = max(max_depth, current_depth + get_switch_depth())
        elif t == '{':
            just_popped_do = False
            stack.append(('NORMAL_BLOCK', '{'))
        elif t == '}':
            if stack:
                popped_type, popped_kw = stack.pop()
                if popped_type == 'BLOCK':
                    current_depth -= 1
                    just_popped_do = (popped_kw == 'do')
                elif popped_type == 'SWITCH':
                    if switch_cases: switch_cases.pop()
                    just_popped_do = False
                elif popped_type == 'NORMAL_BLOCK':
                    just_popped_do = False
                
                if not just_popped_do: cascade_pop_single()
        elif t == ';':
            if not cascade_pop_single(): just_popped_do = False

    final_cli = max_depth - 1 if max_depth > 0 else 0
    cl_metric = round(CL / N, 3)

    lbl_cl.config(text=f"Абсолютная сложность (CL): {CL}")
    lbl_cl_rel.config(text=f"Относительная сложность (cl): {cl_metric}  ({CL}/{N})")
    lbl_cli.config(text=f"Макс. уровень вложенности (CLI): {final_cli}")

root = tk.Tk()
root.title("Парсер метрик Джилба")
root.geometry("600x500")
root.configure(padx=10, pady=10)
tk.Label(root, text="Вставьте TypeScript код:", font=("Arial", 11, "bold")).pack(anchor="w")
text_area = scrolledtext.ScrolledText(root, width=70, height=18, font=("Courier", 10))
text_area.pack(pady=5)
btn_analyze = tk.Button(root, text="Рассчитать метрики", font=("Arial", 11, "bold"), bg="#4CAF50", fg="white", command=calculate_metrics)
btn_analyze.pack(pady=10)
lbl_cl = tk.Label(root, text="Абсолютная сложность (CL): -", font=("Arial", 12))
lbl_cl.pack(anchor="w")
lbl_cl_rel = tk.Label(root, text="Относительная сложность (cl): -", font=("Arial", 12))
lbl_cl_rel.pack(anchor="w")
lbl_cli = tk.Label(root, text="Макс. уровень вложенности (CLI): -", font=("Arial", 12))
lbl_cli.pack(anchor="w")
root.mainloop()