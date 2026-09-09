from __future__ import annotations

import math
import re
import tkinter as tk
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from tkinter import filedialog, messagebox, ttk


OPERATORS = {
    "as", "asserts", "async", "await", "break", "case", "catch", "class",
    "const", "constructor", "continue", "debugger", "declare", "default",
    "delete", "do", "else", "enum", "export", "extends", "finally", "for",
    "from", "function", "get", "if", "implements", "import", "in", "infer",
    "instanceof", "interface", "keyof", "let", "module", "namespace", "new",
    "of", "private", "protected", "public", "readonly", "return", "set",
    "static", "super", "switch", "satisfies", "throw", "try", "typeof",
    "var", "void", "while", "with", "yield", "is",
}

OPERATOR_SYMBOLS = (
    "===", "!==", ">>>=", "**=", "&&=", "||=", "??=", "...", "=>", "?.",
    "++", "--", "==", "!=", "<=", ">=", "&&", "||", "??", "**", "+=", "-=",
    "*=", "/=", "%=", "<<", ">>", ">>>", "&=", "|=", "^=", "?.", "=", "+",
    "-", "*", "/", "%", "<", ">", "!", "&", "|", "^", "~", "?", ":",
    ".", ";", ",", "(", ")", "()", "[", "]", "[]", "{", "}", "{}", "${}",
)

STANDARD_OPERATORS = tuple(sorted(set(OPERATORS) | set(OPERATOR_SYMBOLS)))

TOKEN_RE = re.compile(
    r"(?P<space>\s+)"
    r"|(?P<line>//[^\n]*)"
    r"|(?P<block>/\*[\s\S]*?\*/)"
    r"|(?P<string>`(?:\\.|[^`])*`|'(?:\\.|[^'\\])*'|\"(?:\\.|[^\"\\])*\")"
    r"|(?P<number>(?:0[xX][0-9a-fA-F]+|\d+(?:\.\d+)?(?:[eE][+-]?\d+)?))"
    r"|(?P<word>[A-Za-z_$][\w$]*)"
    r"|(?P<operator>===|!==|>>>=|\*\*=|&&=|\|\|=|\?\?=|\.\.\.|=>|\?\.|\+\+|--|==|!=|<=|>=|&&|\|\||\?\?|\*\*|\+=|-=|\*=|/=|%=|<<|>>|>>>|&=|\|=|\^=|[=+\-*/%<>&|^~!?:.,;()[\]{}])"
)


@dataclass
class Analysis:
    operators: Counter[str]
    operands: Counter[str]
    unknown: list[str]

    @property
    def n1(self) -> int:
        return len(self.operators)

    @property
    def n2(self) -> int:
        return len(self.operands)

    @property
    def N1(self) -> int:
        return sum(self.operators.values())

    @property
    def N2(self) -> int:
        return sum(self.operands.values())

    @property
    def vocabulary(self) -> int:
        return self.n1 + self.n2

    @property
    def length(self) -> int:
        return self.N1 + self.N2

    @property
    def volume(self) -> float:
        return self.length * math.log2(self.vocabulary) if self.vocabulary > 1 else 0.0

    @property
    def difficulty(self) -> float:
        return (self.n1 / 2) * (self.N2 / self.n2) if self.n2 else 0.0

    @property
    def effort(self) -> float:
        return self.volume * self.difficulty


@dataclass(frozen=True)
class LexToken:
    kind: str
    value: str


def _find_interpolation_end(source: str, start: int) -> int:
    depth = 1
    pos = start
    while pos < len(source):
        char = source[pos]
        if char == "\\":
            pos += 2
            continue
        if char in ("'", '"'):
            quote = char
            pos += 1
            while pos < len(source):
                if source[pos] == "\\":
                    pos += 2
                elif source[pos] == quote:
                    pos += 1
                    break
                else:
                    pos += 1
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return pos
        pos += 1
    return len(source) - 1


def _consume_template(source: str, start: int) -> tuple[int, list[tuple[str, str]]]:
    parts: list[tuple[str, str]] = []
    pos = start + 1
    text_start = pos
    while pos < len(source):
        if source[pos] == "\\":
            pos += 2
            continue
        if source[pos] == "`":
            if pos > text_start:
                parts.append(("text", source[text_start:pos]))
            return pos + 1, parts
        if source.startswith("${", pos):
            if pos > text_start:
                parts.append(("text", source[text_start:pos]))
            end = _find_interpolation_end(source, pos + 2)
            parts.append(("code", source[pos + 2:end]))
            pos = end + 1
            text_start = pos
            continue
        pos += 1
    if text_start < len(source):
        parts.append(("text", source[text_start:]))
    return len(source), parts


def _lex_typescript(source: str) -> tuple[list[LexToken], list[str]]:
    tokens: list[LexToken] = []
    unknown: list[str] = []
    pos = 0
    while pos < len(source):
        if source[pos] == "`":
            end, parts = _consume_template(source, pos)
            for part_type, part in parts:
                if part_type == "text":
                    if part:
                        tokens.append(LexToken("operand", f"`{part}`"))
                else:
                    tokens.append(LexToken("operator", "${}"))
                    nested_tokens, nested_unknown = _lex_typescript(part)
                    tokens.extend(nested_tokens)
                    unknown.extend(nested_unknown)
            pos = end
            continue
        match = TOKEN_RE.match(source, pos)
        if not match:
            unknown.append(source[pos])
            pos += 1
            continue
        kind = match.lastgroup
        value = match.group()
        pos = match.end()
        if kind in ("space", "line", "block"):
            continue
        token_kind = "operator" if kind == "operator" else kind
        tokens.append(LexToken(token_kind, value))
    return tokens, unknown


def _matching(tokens: list[LexToken], start: int, opening: str, closing: str) -> int | None:
    depth = 0
    for index in range(start, len(tokens)):
        value = tokens[index].value
        if value == opening:
            depth += 1
        elif value == closing:
            depth -= 1
            if depth == 0:
                return index
    return None


def _statement_end(tokens: list[LexToken], start: int) -> int:
    depth = 0
    for index in range(start, len(tokens)):
        value = tokens[index].value
        if value in {"{", "[", "("}:
            depth += 1
        elif value in {"}", "]", ")"}:
            depth = max(0, depth - 1)
        elif value == ";" and depth == 0:
            return index
    return len(tokens)


def _remove_declarations(tokens: list[LexToken]) -> list[LexToken]:
    result: list[LexToken] = []
    index = 0
    while index < len(tokens):
        value = tokens[index].value
        previous_value = tokens[index - 1].value if index else ""
        if value == "export":
            index += 1
            continue
        if value == "interface" and index + 2 < len(tokens):
            open_index = next((i for i in range(index + 1, len(tokens)) if tokens[i].value == "{"), None)
            if open_index is not None:
                close_index = _matching(tokens, open_index, "{", "}")
                index = (close_index + 1) if close_index is not None else len(tokens)
                continue
        if value == "type" and previous_value in {"", "export", "declare", ";", "}"}:
            index = _statement_end(tokens, index + 1) + 1
            continue
        if value in {"import", "declare"}:
            index = _statement_end(tokens, index + 1) + 1
            continue
        result.append(tokens[index])
        index += 1
    return result


def _is_function_parameter_list(tokens: list[LexToken], open_index: int) -> bool:
    before = [token.value for token in tokens[max(0, open_index - 3):open_index]]
    if "function" in before:
        return True
    close_index = _matching(tokens, open_index, "(", ")")
    return close_index is not None and close_index + 1 < len(tokens) and tokens[close_index + 1].value == "=>"


def _remove_type_annotations(tokens: list[LexToken]) -> list[LexToken]:
    result: list[LexToken] = []
    paren_stack: list[tuple[int, bool]] = []
    declaration_since_boundary = False
    index = 0
    skip_until: str | None = None
    while index < len(tokens):
        value = tokens[index].value
        if skip_until is not None:
            if value in {skip_until, "=", ";", "{", "=>"}:
                skip_until = None
                if value in {"=", ";", "{", "=>"}:
                    result.append(tokens[index])
                index += 1
                continue
            index += 1
            continue
        if value in {"const", "let", "var"}:
            declaration_since_boundary = True
            index += 1
            continue
        if value in {";", "{", "=", ","}:
            declaration_since_boundary = False
        if value == "(":
            paren_stack.append((index, _is_function_parameter_list(tokens, index)))
        elif value == ")" and paren_stack:
            paren_stack.pop()
        if value == ":":
            in_function_params = bool(paren_stack and paren_stack[-1][1])
            previous = tokens[index - 1].value if index else ""
            return_annotation = previous == ")"
            if in_function_params or declaration_since_boundary or return_annotation:
                result_before = result
                if result_before and result_before[-1].value == ":":
                    result_before.pop()
                index += 1
                while index < len(tokens) and tokens[index].value not in {",", ")", "=", ";", "{", "=>"}:
                    index += 1
                continue
        result.append(tokens[index])
        index += 1
    return result


CONTROL_WORDS = {"if", "for", "while", "switch", "catch", "with"}


def _if_else_indices(tokens: list[LexToken]) -> tuple[set[int], set[int]]:
    if_indices: set[int] = set()
    else_indices: set[int] = set()
    for index, token in enumerate(tokens):
        if token.value != "if" or index + 1 >= len(tokens) or tokens[index + 1].value != "(":
            continue
        close_paren = _matching(tokens, index + 1, "(", ")")
        if close_paren is None or close_paren + 1 >= len(tokens):
            continue
        body_start = close_paren + 1
        if tokens[body_start].value == "{":
            body_end = _matching(tokens, body_start, "{", "}")
        else:
            body_end = next((i for i in range(body_start, len(tokens)) if tokens[i].value == ";"), None)
        if body_end is not None and body_end + 1 < len(tokens) and tokens[body_end + 1].value == "else":
            if_indices.add(index)
            else_indices.add(body_end + 1)
    return if_indices, else_indices


def _is_code_block(tokens: list[LexToken], index: int) -> bool:
    previous = tokens[index - 1].value if index else ""
    return previous in {")", "else", "try", "finally", "do", "=>"
    }


def tokenize_typescript(source: str) -> Analysis:
    tokens, unknown = _lex_typescript(source)
    tokens = _remove_declarations(tokens)
    tokens = _remove_type_annotations(tokens)
    operators: Counter[str] = Counter()
    operands: Counter[str] = Counter()
    if_indices, else_indices = _if_else_indices(tokens)
    skipped_closing_braces: set[int] = set()
    case_label_colons: set[int] = set()
    object_colons: set[int] = set()
    for brace_index, brace in enumerate(tokens):
        if brace.value != "{":
            continue
        close_brace = _matching(tokens, brace_index, "{", "}")
        if close_brace is None:
            continue
        if not _is_code_block(tokens, brace_index):
            object_colons.update(
                i for i in range(brace_index + 1, close_brace) if tokens[i].value == ":"
            )
    index = 0
    while index < len(tokens):
        token = tokens[index]
        value = token.value
        if index in skipped_closing_braces:
            index += 1
            continue
        if index in else_indices:
            index += 1
            continue
        if index in if_indices:
            operators["if...else"] += 1
            index += 1
            continue
        if value == "if":
            operators["if"] += 1
            index += 1
            continue
        if value == "switch":
            operators["switch...case"] += 1
            index += 1
            continue
        if value in {"case", "default"}:
            colon_index = next((i for i in range(index + 1, len(tokens)) if tokens[i].value == ":"), None)
            if colon_index is not None:
                case_label_colons.add(colon_index)
            index += 1
            continue
        if index in case_label_colons or index in object_colons:
            index += 1
            continue
            index += 1
            continue
        if value in {"const", "let", "var", "export", "function"}:
            index += 1
            continue
        if value == "{" or value == "}":
            if value == "{":
                operators["{}"] += 1
                close_index = _matching(tokens, index, "{", "}")
                if close_index is not None:
                    skipped_closing_braces.add(close_index)
            index += 1
            continue
        if token.kind == "word" and index + 1 < len(tokens) and tokens[index + 1].value == "(":
            if value not in CONTROL_WORDS and value not in {"function"}:
                operators[value] += 1
                index += 1
                continue
        if token.kind == "word" and value in OPERATORS:
            operators[value] += 1
        elif token.kind == "operator":
            operators[value] += 1
        else:
            operands[value] += 1
        index += 1
    round_pairs = min(operators.get("(", 0), operators.get(")", 0))
    if round_pairs:
        operators["("] -= round_pairs
        operators[")"] -= round_pairs
        operators["()"] += round_pairs
        if operators["("] == 0:
            del operators["("]
        if operators[")"] == 0:
            del operators[")"]
    square_pairs = min(operators.get("[", 0), operators.get("]", 0))
    if square_pairs:
        operators["["] -= square_pairs
        operators["]"] -= square_pairs
        operators["[]"] += square_pairs
        if operators["["] == 0:
            del operators["["]
        if operators["]"] == 0:
            del operators["]"]
    return Analysis(operators, operands, unknown)


SAMPLE_CODE = """interface User { id: number; name: string; active: boolean; }

function formatUser(user: User, prefix: string): string {
  if (!user.active) return `${prefix}: inactive`;
  return `${prefix}: ${user.name}`;
}

function summarize(users: User[]): number {
  let active = 0;
  for (const user of users) {
    if (user.active) active += 1;
  }
  return active;
}

const users: User[] = [
  { id: 1, name: "Ada", active: true },
  { id: 2, name: "Linus", active: false },
];
console.log(formatUser(users[0], "User"));
console.log(summarize(users));
"""


class HalsteadApp(tk.Tk):
    BG = "#f3f4f6"
    PANEL = "#ffffff"
    PANEL_2 = "#fafafa"
    TEXT = "#202124"
    MUTED = "#687078"
    ACCENT = "#2f7d5b"
    ACCENT_DARK = "#dceee5"
    BORDER = "#d4d8dc"
    ORANGE = "#9a641f"

    def __init__(self) -> None:
        super().__init__()
        self.title("Анализатор метрик Холстеда")
        self.geometry("1180x760")
        self.minsize(980, 650)
        self.configure(bg=self.BG)
        self.current_file = "Встроенный пример TypeScript"
        self.analysis = tokenize_typescript(SAMPLE_CODE)
        self._configure_styles()
        self._build_ui()
        self._set_code(SAMPLE_CODE)
        self._refresh_report()

    def _configure_styles(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background=self.BG)
        style.configure("Panel.TFrame", background=self.PANEL)
        style.configure("TLabel", background=self.BG, foreground=self.TEXT, font=("Arial", 10))
        style.configure("Muted.TLabel", background=self.BG, foreground=self.MUTED, font=("Arial", 10))
        style.configure("Title.TLabel", background=self.BG, foreground=self.TEXT, font=("Arial", 17, "bold"))
        style.configure("Section.TLabel", background=self.PANEL, foreground=self.TEXT, font=("Arial", 11, "bold"))
        style.configure("Metric.TLabel", background=self.PANEL_2, foreground=self.TEXT, font=("Arial", 14, "bold"))
        style.configure("MetricName.TLabel", background=self.PANEL_2, foreground=self.MUTED, font=("Arial", 9))
        style.configure("TButton", background="#e6e8eb", foreground=self.TEXT, borderwidth=1, padding=(10, 6), font=("Arial", 10))
        style.map("TButton", background=[("active", self.ACCENT_DARK)], foreground=[("active", self.TEXT)])
        style.configure("Accent.TButton", background="#d9ebdf", foreground="#1b5139", padding=(12, 7), font=("Arial", 10, "bold"))
        style.map("Accent.TButton", background=[("active", "#c4e0ce")])
        style.configure("Treeview", background=self.PANEL_2, fieldbackground=self.PANEL_2, foreground=self.TEXT, rowheight=26, borderwidth=1, font=("Arial", 10))
        style.configure("Treeview.Heading", background="#e9ecef", foreground=self.TEXT, relief="flat", padding=(7, 6), font=("Arial", 10, "bold"))
        style.map("Treeview", background=[("selected", self.ACCENT_DARK)], foreground=[("selected", self.TEXT)])
        style.configure("TNotebook", background=self.BG, borderwidth=0)
        style.configure("TNotebook.Tab", background=self.PANEL, foreground=self.MUTED, padding=(16, 8), font=("Arial", 10, "bold"))
        style.map("TNotebook.Tab", background=[("selected", self.PANEL_2)], foreground=[("selected", self.ACCENT)])

    def _build_ui(self) -> None:
        top = ttk.Frame(self, padding=(28, 22, 28, 14))
        top.pack(fill="x")
        ttk.Label(top, text="Анализатор метрик Холстеда", style="Title.TLabel").pack(side="left")
        ttk.Label(top, text="TypeScript", style="Muted.TLabel").pack(side="left", padx=(10, 0), pady=(4, 0))
        ttk.Button(top, text="Сохранить отчёт", command=self._export_report).pack(side="right")
        ttk.Button(top, text="Открыть файл", command=self._open_file).pack(side="right", padx=(0, 8))

        body = ttk.Frame(self, padding=(28, 0, 28, 24))
        body.pack(fill="both", expand=True)
        left = ttk.Frame(body, style="Panel.TFrame", padding=18)
        left.pack(side="left", fill="both", expand=True, padx=(0, 14))
        right = ttk.Frame(body, style="Panel.TFrame", padding=18, width=530)
        right.pack(side="right", fill="both", expand=True)
        right.pack_propagate(False)

        head = ttk.Frame(left, style="Panel.TFrame")
        head.pack(fill="x", pady=(0, 12))
        ttk.Label(head, text="Исходный код", style="Section.TLabel").pack(side="left")
        self.file_label = ttk.Label(head, text=self.current_file, style="Muted.TLabel")
        self.file_label.pack(side="right")
        editor_wrap = tk.Frame(left, bg=self.BORDER, bd=1, relief="solid")
        editor_wrap.pack(fill="both", expand=True)
        self.line_numbers = tk.Text(editor_wrap, width=4, padx=8, pady=10, bg="#edf0f2", fg="#89929a", insertwidth=0, state="disabled", relief="flat", font=("Menlo", 10), takefocus=0)
        self.line_numbers.pack(side="left", fill="y")
        self.editor = tk.Text(editor_wrap, wrap="none", undo=True, bg="#ffffff", fg=self.TEXT, insertbackground=self.ACCENT, selectbackground=self.ACCENT_DARK, relief="flat", padx=10, pady=10, font=("Menlo", 10), tabs=("    "))
        self.editor.pack(side="left", fill="both", expand=True)
        scroll = ttk.Scrollbar(editor_wrap, orient="vertical", command=self._scroll_editor)
        scroll.pack(side="right", fill="y")
        self.editor.configure(yscrollcommand=lambda *args: (scroll.set(*args), self._sync_lines()))
        self.editor.bind("<KeyRelease>", lambda _event: self._sync_lines())
        ttk.Button(left, text="Анализировать код", style="Accent.TButton", command=self._analyze).pack(fill="x", pady=(14, 0))

        ttk.Label(right, text="Результаты анализа", style="Section.TLabel").pack(anchor="w")
        self.status = ttk.Label(right, text="Готово к проверке", style="Muted.TLabel")
        self.status.pack(anchor="w", pady=(4, 14))
        self.notebook = ttk.Notebook(right)
        self.notebook.pack(fill="both", expand=True)
        self.summary_tab = ttk.Frame(self.notebook, style="Panel.TFrame", padding=(0, 4, 0, 0))
        self.details_tab = ttk.Frame(self.notebook, style="Panel.TFrame", padding=(0, 4, 0, 0))
        self.check_tab = ttk.Frame(self.notebook, style="Panel.TFrame", padding=(0, 4, 0, 0))
        self.notebook.add(self.summary_tab, text="Сводка")
        self.notebook.add(self.details_tab, text="Словари")
        self.notebook.add(self.check_tab, text="Сверка")
        self._build_summary()
        self._build_details()
        self._build_check()

    def _build_summary(self) -> None:
        self.cards_frame = ttk.Frame(self.summary_tab, style="Panel.TFrame")
        self.cards_frame.pack(fill="x", pady=(0, 14))
        self.card_values: dict[str, ttk.Label] = {}
        for col, (key, name) in enumerate((("n1", "n₁ уник. операторов"), ("n2", "n₂ уник. операндов"), ("N1", "N₁ операторов"), ("N2", "N₂ операндов"))):
            card = ttk.Frame(self.cards_frame, style="Panel.TFrame", padding=12)
            card.grid(row=0, column=col, sticky="nsew", padx=(0 if col == 0 else 5, 5 if col < 3 else 0))
            value = ttk.Label(card, text="0", style="Metric.TLabel", anchor="w")
            value.pack(fill="x")
            ttk.Label(card, text=name, style="MetricName.TLabel").pack(anchor="w", pady=(4, 0))
            self.card_values[key] = value
            self.cards_frame.columnconfigure(col, weight=1)
        ttk.Label(self.summary_tab, text="Базовые и расширенные метрики", style="Section.TLabel").pack(anchor="w", pady=(0, 8))
        self.metric_table = ttk.Treeview(self.summary_tab, columns=("metric", "value", "meaning", "formula"), show="headings", height=11)
        for col, title, width in (("metric", "Метрика", 90), ("value", "Значение", 110), ("meaning", "Что означает", 190), ("formula", "Формула", 170)):
            self.metric_table.heading(col, text=title)
            self.metric_table.column(col, width=width, anchor="w")
        self.metric_table.pack(fill="both", expand=True)
        note = tk.Label(self.summary_tab, text="Правила методички: объявления interface/type и аннотации типов исключаются; имена функций считаются операторами; if...else, switch...case, пары {}, () и [] объединяются. Код внутри ${...} разбирается отдельно.", bg=self.PANEL, fg=self.MUTED, anchor="w", justify="left", wraplength=480, padx=4, pady=12, font=("Arial", 9))
        note.pack(fill="x", pady=(12, 0))

    def _build_details(self) -> None:
        self.details_tab.columnconfigure(0, weight=1)
        self.details_tab.columnconfigure(1, weight=1)
        for col, title in enumerate(("Операторы", "Операнды")):
            ttk.Label(self.details_tab, text=title, style="Section.TLabel").grid(row=0, column=col, sticky="w", padx=(0, 8), pady=(0, 8))
        self.operator_table = self._make_count_table(self.details_tab, 0)
        self.operand_table = self._make_count_table(self.details_tab, 1)
        ttk.Label(self.details_tab, text="В словарь операторов входят основные конструкции TypeScript, даже если их нет в текущем файле. Нулевая частота означает, что токен не встретился в выбранной программе.", style="Muted.TLabel", wraplength=480, justify="left").grid(row=2, column=0, columnspan=2, sticky="we", pady=(14, 0))

    def _make_count_table(self, parent: ttk.Frame, column: int) -> ttk.Treeview:
        wrapper = ttk.Frame(parent, style="Panel.TFrame")
        wrapper.grid(row=1, column=column, sticky="nsew", padx=(0, 8 if column == 0 else 0))
        wrapper.columnconfigure(0, weight=1)
        wrapper.rowconfigure(0, weight=1)
        table = ttk.Treeview(wrapper, columns=("token", "count"), show="headings", height=16)
        table.heading("token", text="Токен")
        table.heading("count", text="Количество")
        table.column("token", width=150, anchor="w")
        table.column("count", width=100, anchor="center")
        table.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(wrapper, orient="vertical", command=table.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        table.configure(yscrollcommand=scrollbar.set)
        parent.rowconfigure(1, weight=1)
        return table

    def _build_check(self) -> None:
        ttk.Label(self.check_tab, text="Ручной расчёт", style="Section.TLabel").pack(anchor="w")
        ttk.Label(self.check_tab, text="Введите значения из самостоятельной таблицы преподавателя и нажмите «Сравнить».", style="Muted.TLabel", wraplength=480, justify="left").pack(anchor="w", pady=(4, 14))
        input_frame = ttk.Frame(self.check_tab, style="Panel.TFrame")
        input_frame.pack(fill="x")
        self.manual_vars: dict[str, tk.StringVar] = {}
        for row, key in enumerate(("n1", "n2", "N1", "N2")):
            ttk.Label(input_frame, text=key, style="Muted.TLabel", width=5).grid(row=row, column=0, sticky="w", pady=4)
            var = tk.StringVar()
            ttk.Entry(input_frame, textvariable=var, width=14).grid(row=row, column=1, sticky="w", pady=4)
            self.manual_vars[key] = var
        ttk.Button(input_frame, text="Сравнить", command=self._compare_manual).grid(row=0, column=2, rowspan=4, padx=(18, 0), sticky="ns")
        self.compare_table = ttk.Treeview(self.check_tab, columns=("metric", "manual", "program", "same"), show="headings", height=8)
        for col, title, width in (("metric", "Метрика", 100), ("manual", "Ручной расчёт", 125), ("program", "Программа", 105), ("same", "Совпадает", 100)):
            self.compare_table.heading(col, text=title)
            self.compare_table.column(col, width=width, anchor="center")
        self.compare_table.pack(fill="x", pady=(18, 0))
        ttk.Label(self.check_tab, text="Сверяются четыре исходных величины n₁, n₂, N₁ и N₂. Остальные значения вычисляются из них автоматически.", style="Muted.TLabel", wraplength=480, justify="left").pack(anchor="w", pady=(14, 0))

    def _set_code(self, code: str) -> None:
        self.editor.delete("1.0", "end")
        self.editor.insert("1.0", code)
        self._sync_lines()

    def _sync_lines(self) -> None:
        if not hasattr(self, "line_numbers"):
            return
        count = int(self.editor.index("end-1c").split(".")[0])
        self.line_numbers.configure(state="normal")
        self.line_numbers.delete("1.0", "end")
        self.line_numbers.insert("1.0", "\n".join(str(i) for i in range(1, count + 1)))
        self.line_numbers.configure(state="disabled")

    def _scroll_editor(self, *args: str) -> None:
        self.editor.yview(*args)
        self.line_numbers.yview(*args)

    def _open_file(self) -> None:
        path = filedialog.askopenfilename(title="Выберите TypeScript-файл", filetypes=(("TypeScript", "*.ts *.tsx"), ("Все файлы", "*.*")))
        if not path:
            return
        try:
            code = Path(path).read_text(encoding="utf-8")
        except UnicodeDecodeError:
            code = Path(path).read_text(encoding="utf-8-sig")
        self.current_file = Path(path).name
        self.file_label.configure(text=self.current_file)
        self._set_code(code)
        self._analyze()

    def _analyze(self) -> None:
        self.analysis = tokenize_typescript(self.editor.get("1.0", "end-1c"))
        self._refresh_report()
        self.status.configure(text=f"Проанализировано: {self.analysis.length} токенов  ·  {self.current_file}", foreground=self.ACCENT)

    @staticmethod
    def _fmt(number: float) -> str:
        return str(int(number)) if float(number).is_integer() else f"{number:.3f}"

    def _refresh_report(self) -> None:
        a = self.analysis
        for key in ("n1", "n2", "N1", "N2"):
            self.card_values[key].configure(text=str(getattr(a, key)))
        for item in self.metric_table.get_children():
            self.metric_table.delete(item)
        rows = (
            ("n₁", a.n1, "уникальные операторы", "|O|"),
            ("n₂", a.n2, "уникальные операнды", "|D|"),
            ("N₁", a.N1, "общее число операторов", "Σ O"),
            ("N₂", a.N2, "общее число операндов", "Σ D"),
            ("n", a.vocabulary, "словарь программы", "n₁ + n₂"),
            ("N", a.length, "длина программы", "N₁ + N₂"),
            ("V", a.volume, "объём программы", "N · log₂(n)"),
            ("D", a.difficulty, "сложность", "(n₁ / 2) · (N₂ / n₂)"),
            ("E", a.effort, "трудоёмкость", "D · V"),
        )
        for metric, value, meaning, formula in rows:
            self.metric_table.insert("", "end", values=(metric, self._fmt(value), meaning, formula))
        operator_dictionary = Counter({token: a.operators.get(token, 0) for token in STANDARD_OPERATORS})
        operator_dictionary.update({token: count for token, count in a.operators.items() if token not in operator_dictionary})
        for table, counter in ((self.operator_table, operator_dictionary), (self.operand_table, a.operands)):
            for item in table.get_children():
                table.delete(item)
            items = sorted(counter.items()) if table is self.operator_table else sorted(counter.items(), key=lambda pair: (-pair[1], pair[0]))
            for token, count in items:
                table.insert("", "end", values=(token, count))

    def _compare_manual(self) -> None:
        a = self.analysis
        for item in self.compare_table.get_children():
            self.compare_table.delete(item)
        for key in ("n1", "n2", "N1", "N2"):
            manual = self.manual_vars[key].get().strip()
            program = str(getattr(a, key))
            same = "Да" if manual.isdigit() and int(manual) == getattr(a, key) else "Нет"
            self.compare_table.insert("", "end", values=(key, manual or "—", program, same))

    def _export_report(self) -> None:
        path = filedialog.asksaveasfilename(title="Сохранить отчёт", defaultextension=".txt", filetypes=(("Текстовый отчёт", "*.txt"), ("CSV таблица", "*.csv")))
        if not path:
            return
        a = self.analysis
        lines = ["ОТЧЁТ ПО МЕТРИКАМ ХОЛСТЕДА", f"Файл: {self.current_file}", "", "Метрика\tЗначение"]
        lines += [f"{name}\t{self._fmt(value)}" for name, value in (("n1", a.n1), ("n2", a.n2), ("N1", a.N1), ("N2", a.N2), ("n", a.vocabulary), ("N", a.length), ("V", a.volume), ("D", a.difficulty), ("E", a.effort))]
        lines += ["", "ОПЕРАТОРЫ", "Токен\tКоличество"]
        operator_dictionary = Counter({token: a.operators.get(token, 0) for token in STANDARD_OPERATORS})
        operator_dictionary.update({token: count for token, count in a.operators.items() if token not in operator_dictionary})
        lines += [f"{token}\t{count}" for token, count in sorted(operator_dictionary.items())]
        lines += ["", "ОПЕРАНДЫ", "Токен\tКоличество"]
        lines += [f"{token}\t{count}" for token, count in sorted(a.operands.items())]
        Path(path).write_text("\n".join(lines), encoding="utf-8")
        messagebox.showinfo("Отчёт сохранён", f"Файл записан:\n{path}")


if __name__ == "__main__":
    app = HalsteadApp()
    app.mainloop()
