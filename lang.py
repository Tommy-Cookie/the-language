
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
	Comma = 12


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
	Tk.Comma: r",",
	
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
		if name in self.frames[-1]:
			self.error(f"redefine identifier '{name}'")
		
		self.frames[-1][name] = value


	def set_frame_variable(self, name: str, value: Any):
		for frame in self.frames[::-1]:
			if name in frame:
				frame[name] = value
				return

		self.error(f"identifier '{name}' doesn't exist")


	def get_frame_variable(self, name: str) -> Any:
		for frame in self.frames[::-1]:
			if name in frame:
				return frame[name]

		self.error(f"identifier '{name}' doesn't exist")


	def get_frame_address(self, name: str) -> int:
		for i, frame in enumerate(self.frames[::-1]):
			if name in frame:
				return i

		self.error(f"identifier '{name}' doesn't exist")


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


	# TODO: make it work for all possible cases
	# `tree` is the address, see line 138 for tree structure
	def set_value_to_address(self, addr_tree: list, val: Any, is_top = True):
		if isinstance(addr_tree, Token):
			if is_top:
				addr = self.get_frame_address(addr_tree.val)
				self.frames[addr][addr_tree.val] = val
			return

		self.error("NOT IMPLEMENTED")


	#region Pratt Parsing

	# TODO: pratt paring
	# tree structure:
	# [lhs, rhs, op] e.g. [1, [3, 2, Tk.Plus], Tk.Star]
	def evaluate_next_to_tree(self, min_bp = 0) -> Any:
		tok = self.next_token()
		lhs = None

		if tok == Tk.Int or tok == Tk.Float:
			lhs = tok
		elif tok == Tk.Id:
			lhs = tok
		elif tok == Tk.LeftParen:
			lhs = self.evaluate_next_to_tree()

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
			elif op == Tk.Comma:
				break

			l_bp, r_bp = self.infix_binding_power(op)
			if l_bp < min_bp:
				break

			self.next_token()

			if op == Tk.LeftParen: # function call
				rhs = []
				while True:
					peek = self.peek_token()
					if peek == Tk.RightParen:
						self.next_token()
						break
					if peek == Tk.Comma:
						self.next_token()
					rhs.append(self.evaluate_next_to_tree())
			else:
				rhs = self.evaluate_next_to_tree(r_bp)

			lhs = [lhs, rhs, op]

		return lhs


	def infix_binding_power(self, op: Tk) -> tuple:
		match op:
			case Tk.Equal:
				return 101, 100
			case Tk.Plus:
				return 111, 110
			case Tk.Star:
				return 121, 120
			case Tk.LeftParen: # function call
				return 1001, 1000
			case _:
				self.error(f"unknow operation {op}")

	#endregion

	#region Run

	def evaluate_tree(self, tree: list):
		if isinstance(tree, Token):
			if tree == Tk.Int or tree == Tk.Float:
				return tree.val
			elif tree == Tk.Id:
				return self.get_frame_variable(tree.val)

		op = tree[2]

		if op == Tk.Equal:
			lhs = tree[0]
		else:
			lhs = self.evaluate_tree(tree[0])
		rhs = self.evaluate_tree(tree[1])

		match op:
			case Tk.Plus:
				return lhs + rhs
			case Tk.Star:
				return lhs * rhs
			case Tk.Equal:
				self.set_value_to_address(lhs, rhs)
				return rhs
			case _:
				self.error(f"unknow operation {op}")


	def run(self, modify_frames = True):
		self.ptr = 0

		if modify_frames:
			self.frames.append({})

		while self.ptr < len(self.tokens):
			first = self.tokens[self.ptr].val

			if first == "let":
				name = self.expect_next_token(Tk.Id).val
				self.expect_next_token(Tk.Equal)
				tree = self.evaluate_next_to_tree()
				value = self.evaluate_tree(tree)

				self.create_frame_variable(name, value)
			
			else:
				self.ptr -= 1
				tree = self.evaluate_next_to_tree()
				print(tree)
				self.evaluate_tree(tree)

			# asserts semi colon
			self.expect_next_token(Tk.Semi)

			self.ptr += 1

		if modify_frames:
			self.frames.pop()

	#endregion


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
