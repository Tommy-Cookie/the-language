
import re
import sys
from enum import Enum
from dataclasses import dataclass
from typing import Any, Callable


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
	Slash = 13
	Minus = 14
	String = 15
	LeftBraket = 16
	RightBraket = 17
	Data = 18 # use to mark lists into data lists


class Typ(Enum):
	Int = 0
	Float = 1
	String = 2
	Array = 3
	Id = 4


TOKEN_PATTERN = {
	Tk.Key_Let: r"let",

	Tk.String: r"\"[\S\s]*?\"",
	Tk.Useless: r"\/\/[^\n]*|\/\*[\S\s]*?\*\/",
	
	Tk.Id: r"[a-zA-Z_][a-zA-Z0-9_]*",
	Tk.Equal: r"=",
	Tk.Float: r"[+-]?([0-9]+)?\.([0-9]+)?",
	Tk.Int: r"[+-]?[0-9]+",
	Tk.Plus: r"\+",
	Tk.Minus: r"-",
	Tk.Star: r"\*",
	Tk.Slash: r"\/",
	Tk.Semi: r";",
	Tk.LeftParen: r"\(",
	Tk.RightParen: r"\)",
	Tk.LeftBraket: r"\[",
	Tk.RightBraket: r"\]",
	Tk.Comma: r",",
	
	Tk.NotAssigned: r"\S"
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
		return False


@dataclass
class Extern:
	callback: Callable
	num_args: int


@dataclass
class Variant:
	typ: Typ
	val: Any

	def __eq__(self, value: object) -> bool:
		if isinstance(value, Typ):
			return self.typ == value
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
		if isinstance(addr_tree, Variant):
			if is_top:
				self.set_frame_variable(addr_tree.val, val)
			else:
				self.error("NOT IMPLEMENTED")
			return

		self.error("NOT IMPLEMENTED")


	#region Pratt Parsing

	# TODO: pratt paring
	# tree structure:
	# [lhs, rhs, op] e.g. [1, [3, 2, Tk.Plus], Tk.Star]
	def evaluate_next_to_tree(self, min_bp = 0) -> Any:
		tok = self.next_token()
		lhs = None

		if tok == Tk.Int:
			lhs = Variant(Typ.Int, tok.val)
		elif tok == Tk.Float:
			lhs = Variant(Typ.Float, tok.val)
		elif tok == Tk.Id:
			lhs = Variant(Typ.Id, tok.val)
		elif tok == Tk.String:
			lhs = Variant(Typ.String, tok.val)
		elif tok == Tk.LeftParen:
			lhs = self.evaluate_next_to_tree()
			if self.next_token() != Tk.RightParen:
				self.error("mismatched parentheses")
		elif tok == Tk.LeftBraket:
			items = []
			while True:
				peek = self.peek_token()
				if peek == Tk.RightBraket:
					self.next_token()
					break
				if peek == Tk.Comma:
					self.next_token()
				items.append(self.evaluate_next_to_tree())
			lhs = Variant(Typ.Array, items)
		else:
			self.error(f"bad value '{tok.val}'")

		while True:
			tok = self.peek_token()
			op = tok.typ

			if op == Tk.Semi:
				break
			elif op == Tk.RightParen or op == Tk.RightBraket:
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
			elif op == Tk.LeftBraket: # array indexing
				rhs = self.evaluate_next_to_tree()
				if self.next_token() != Tk.RightBraket:
					self.error("mismatched brakets")
			else:
				rhs = self.evaluate_next_to_tree(r_bp)

			lhs = [lhs, rhs, op]

		return lhs


	def infix_binding_power(self, op: Tk) -> tuple:
		match op:
			case Tk.Equal:
				return 101, 100
			case Tk.Plus | Tk.Minus:
				return 111, 110
			case Tk.Star | Tk.Slash:
				return 121, 120
			case Tk.LeftParen | Tk.LeftBraket: # function call | array indexing
				return 1001, 1000
			case _:
				self.error(f"unknow operation {op}")

	#endregion

	#region Run

	def evaluate_tree(self, tree: list) -> Variant:
		if isinstance(tree, Variant):
			if tree == Typ.Int or tree == Typ.Float:
				return tree
			elif tree == Typ.String:
				return tree
			elif tree == Typ.Id:
				return self.get_frame_variable(tree.val)
			elif tree == Typ.Array:
				items = []
				for item in tree.val:
					items.append(self.evaluate_tree(item))
				return Variant(Typ.Array, items)

		op = tree[2]

		if op == Tk.Equal:
			lhs = tree[0]
		else:
			lhs = self.evaluate_tree(tree[0])

		if op == Tk.LeftParen:
			rhs = []
			for arg in tree[1]:
				rhs.append(self.evaluate_tree(arg))
		else:
			rhs = self.evaluate_tree(tree[1])

		def make_variant_based_on_type(val) -> Variant:
			if isinstance(val, float):
				return Variant(Typ.Float, val)
			elif isinstance(val, int):
				return Variant(Typ.Int, val)
			elif isinstance(val, str):
				return Variant(Typ.String, val)
			elif isinstance(val, list):
				return Variant(Typ.Array, val)

			self.error(f"no matching type for value {repr(val)}")

		match op:
			case Tk.Plus:
				return make_variant_based_on_type(lhs.val + rhs.val) # type: ignore
			case Tk.Minus:
				return make_variant_based_on_type(lhs.val - rhs.val) # type: ignore
			case Tk.Star:
				return make_variant_based_on_type(lhs.val * rhs.val) # type: ignore
			case Tk.Slash:
				return make_variant_based_on_type(lhs.val / rhs.val) # type: ignore
			case Tk.Equal:
				self.set_value_to_address(lhs, rhs) # type: ignore
				return self.evaluate_tree(rhs) # type: ignore
			case Tk.LeftParen:
				if isinstance(lhs, Extern):
					if len(rhs) == lhs.num_args: # type: ignore
						return lhs.callback(*rhs) # type: ignore
					self.error(f"{lhs} expects {lhs.num_args} argument(s), got {len(rhs)} instead") # type: ignore
				else:
					self.error(f"{lhs} is not callable")
			case Tk.LeftBraket:
				return lhs.val[rhs.val] # type: ignore
			case _:
				self.error(f"unknow operation {op}")

	#endregion

	#region Run Line

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
				self.evaluate_tree(tree)

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
				case Tk.String:
					val = val[1:-1]

			if typ != Tk.Useless:
				tokens.append(Token(typ, val, line, col))

		self.tokens = tokens


	def run(self):
		self.frames = [
			{"println": Extern(lambda x: print(x.val), 1)},
			{"print": Extern(lambda x: print(x.val, end=""), 1)}
		]

		self.frames.append({})
		root_block = Block(self.tokens, self.frames)
		root_block.run(False)

		print(self.frames)
