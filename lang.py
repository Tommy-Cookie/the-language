
import re
import sys
from enum import Enum
from dataclasses import dataclass
from typing import Any


class Tk(Enum):
	Useless = 0
	Key_Let = 1
	Id = 2
	Equal = 3
	Int = 4
	Plus = 5
	Star = 6
	Semi = 7
	Float = 8
	NotAssigned = 9
	LeftParen = 10
	RightParen = 11


TOKEN_PATTERN = {
	Tk.Key_Let: r"let",

	# NOTE: must place after String pattern 
	Tk.Useless: r"\/\/[^\n]*|\/\*[\S\s]*?\*\/",
	
	Tk.Id: r"[a-zA-Z_][a-zA-Z0-9_]*",
	Tk.Equal: r"=",
	Tk.Float: r"[+-]?([0-9]+)?\.([0-9]+)?",
	Tk.Int: r"[+-]?[0-9]+",
	Tk.Plus: r"\+",
	Tk.Star: r"\*",
	Tk.Semi: r";",
	Tk.LeftParen: r"\(",
	Tk.RightParen: r"\)",
	
	Tk.NotAssigned: r"\S",
}


Variables = dict[str, Any]


@dataclass
class Token:
	typ: Tk
	val: Any
	line: int
	col: int

	def __eq__(self, value: object) -> bool:
		if isinstance(value, Tk):
			return self.typ == value
		else:
			return False


class Block:
	def __init__(self, tokens: list[Token], frames: list[Variables]) -> None:
		self.tokens = tokens
		self.ptr = 0
		self.frames = frames


	def error(self, msg: str):
		tok = self.tokens[min(self.ptr, len(self.tokens) - 1)]
		sys.stderr.write(f"[error] {msg}.\n  at line {tok.line} col {tok.col}")
		sys.exit(1)


	def create_frame_variable(self, name: str, value: Any):
		self.frames[-1][name] = value


	def set_frame_variable(self, name: str, value: Any):
		for i in range(len(self.frames) - 1, -1, -1):
			if name in self.frames[i]:
				self.frames[i][name] = value
				return

		self.error(f"identifier {name} doesn't exist")


	def get_frame_variable(self, name: str) -> Any:
		for frame in self.frames[::-1]:
			if name in frame:
				return frame[name]

		self.error(f"identifier {name} doesn't exist")


	def next_token(self) -> Token:
		self.ptr += 1
		if self.ptr >= len(self.tokens):
			self.error("unexpected EOF")
		return self.tokens[self.ptr]


	def peek_token(self) -> Token:
		val = self.next_token()
		self.ptr -= 1
		return val


	def expect_next_token(self, expected: Tk) -> Token:
		tok = self.next_token()

		if tok == expected:
			return tok

		self.error(f"expected {expected}, got {tok.typ} instead")


	# TODO: pratt paring
	def evaluate_next(self, min_bp = 0) -> Any:
		tok = self.next_token()
		lhs = None

		if tok == Tk.Int or tok == Tk.Float:
			lhs = tok.val
		elif tok == Tk.LeftParen:
			lhs = self.evaluate_next()

			if self.next_token() != Tk.RightParen:
				self.error("mismatched parentheses")
		else:
			self.error(f"bad value '{tok.val}'")

		while True:
			tok = self.peek_token()
			op = tok.typ

			if op == Tk.Semi:
				break
			elif op == Tk.RightParen:
				break

			l_bp, r_bp = self.infix_binding_power(op)
			if l_bp < min_bp:
				break

			self.next_token()

			rhs = self.evaluate_next(r_bp)
			lhs = self.perform_operation(lhs, rhs, op)

		return lhs


	def infix_binding_power(self, op: Tk) -> tuple:
		match op:
			case Tk.Plus:
				return 11, 10
			case Tk.Star:
				return 21, 20
			case _:
				self.error(f"bad operation {op}")


	def perform_operation(self, a, b, op: Tk):
		match op:
			case Tk.Plus:
				return a + b
			case Tk.Star:
				return a * b
			case _:
				self.error(f"bad operation {op}")


	def run(self, modify_frames = True):
		self.ptr = 0

		if modify_frames:
			self.frames.append({})

		while self.ptr < len(self.tokens):
			first = self.tokens[self.ptr].val

			if first == "let":
				name = self.expect_next_token(Tk.Id).val
				self.expect_next_token(Tk.Equal)
				value = self.evaluate_next()

				self.create_frame_variable(name, value)

			# asserts semi colon
			self.expect_next_token(Tk.Semi)

			self.ptr += 1

		if modify_frames:
			self.frames.pop()


class Lang:
	def __init__(self, src: str) -> None:
		self.src = src
		self.tokens = []
		self.frames: list[Variables] = []


	def parse(self):
		combined = "|".join(f"(?P<p{k.value}>{v})" for k, v in TOKEN_PATTERN.items())

		rx = re.compile(combined)
		tokens = []

		for m in rx.finditer(self.src):
			val = m.group()

			typ = Tk.NotAssigned
			if m.lastgroup:
				typ = Tk(int(m.lastgroup[1:]))

			pos = m.start()
			line = self.src.count("\n", 0, pos) + 1
			col = pos - self.src.rfind("\n", 0, pos)

			match typ:
				case Tk.Int:
					val = int(val)
				case Tk.Float:
					val = float(val)

			if typ != Tk.Useless:
				tokens.append(Token(typ, val, line, col))

		self.tokens = tokens


	def run(self):
		print([t.val for t in self.tokens])
		self.frames.append({})

		root_block = Block(self.tokens, self.frames)
		root_block.run(False)

		print(self.frames)
