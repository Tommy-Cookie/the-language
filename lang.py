
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
	LeftBracket = 16
	RightBracket = 17
	LeftBrace = 18
	RightBrace = 19
	Key_If = 20
	Key_Else = 21
	Key_While = 22
	Less = 23
	Greater = 24
	LessEqual = 25
	GreaterEqual = 26
	EqualEqual = 27
	AndAnd = 28
	OrOr = 29


class Typ(Enum):
	Int = 0
	Float = 1
	String = 2
	Array = 3
	Id = 4


TOKEN_PATTERN = {
	Tk.String: r"\"[\S\s]*?\"",

	Tk.Key_Let: r"let",
	Tk.Key_If: r"if",
	Tk.Key_Else: r"else",
	Tk.Key_While: r"while",

	Tk.Useless: r"\/\/[^\n]*|\/\*[\S\s]*?\*\/",
	
	Tk.Id: r"[a-zA-Z_][a-zA-Z0-9_]*",
	Tk.EqualEqual: r"==",
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
	Tk.LeftBracket: r"\[",
	Tk.RightBracket: r"\]",
	Tk.LeftBrace: r"{",
	Tk.RightBrace: r"}",
	Tk.Comma: r",",
	Tk.LessEqual: r"<=",
	Tk.GreaterEqual: r">=",
	Tk.Less: r"<",
	Tk.Greater: r">",
	Tk.AndAnd: r"&&",
	Tk.OrOr: r"\|\|",
	
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

	def __str__(self) -> str:
		match self.typ:
			case Typ.Array:
				return "[" + ", ".join([str(l) for l in self.val]) + "]"
			case _:
				return str(self.val)


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


	def peek_or_useless(self) -> Token:
		if self.ptr + 1 >= len(self.tokens):
			return Token(Tk.Useless, None, 0, 0)
		return self.peek_token()


	# `tree` is the address, see line 138 for tree structure
	def set_value_to_address(self, addr_tree: list, val: Variant):
		addr = self.evaluate_tree(addr_tree)
		addr.typ = val.typ
		addr.val = val.val


	def next_block(self) -> list[Token]:
		self.expect_next_token(Tk.LeftBrace)

		depth = 0
		toks = []

		while True:
			tok = self.next_token()

			if tok == Tk.LeftBrace:
				depth += 1
			if tok == Tk.RightBrace:
				depth -= 1
			if depth < 0:
				return toks

			toks.append(tok)


	def is_true(self, val: Variant) -> bool:
		match val.typ:
			case Typ.Int | Typ.Float:
				return val.val != 0
			case Typ.Array | Typ.String:
				return len(val.val) != 0
			case _:
				return False


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
		elif tok == Tk.LeftBracket:
			items = []
			while True:
				peek = self.peek_token()
				if peek == Tk.RightBracket:
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
			elif op == Tk.RightParen or op == Tk.RightBracket:
				break
			elif op == Tk.Comma:
				break
			elif op == Tk.LeftBrace: # e.g. if (1) { ... }
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
			elif op == Tk.LeftBracket: # array indexing
				rhs = self.evaluate_next_to_tree()
				if self.next_token() != Tk.RightBracket:
					self.error("mismatched brakets")
			else:
				rhs = self.evaluate_next_to_tree(r_bp)

			lhs = [lhs, rhs, op]

		return lhs


	def infix_binding_power(self, op: Tk) -> tuple:
		match op:
			case Tk.OrOr:
				return 71, 70
			case Tk.AndAnd:
				return 81, 80
			case Tk.Less | Tk.Greater | Tk.LessEqual | Tk.GreaterEqual | Tk.EqualEqual:
				return 91, 90
			case Tk.Equal:
				return 101, 100
			case Tk.Plus | Tk.Minus:
				return 111, 110
			case Tk.Star | Tk.Slash:
				return 121, 120
			case Tk.LeftParen | Tk.LeftBracket: # function call | array indexing
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
			case Tk.Less:
				return make_variant_based_on_type(1 if lhs.val < rhs.val else 0) # type: ignore
			case Tk.Greater:
				return make_variant_based_on_type(1 if lhs.val > rhs.val else 0) # type: ignore
			case Tk.LessEqual:
				return make_variant_based_on_type(1 if lhs.val <= rhs.val else 0) # type: ignore
			case Tk.GreaterEqual:
				return make_variant_based_on_type(1 if lhs.val >= rhs.val else 0) # type: ignore
			case Tk.EqualEqual:
				return make_variant_based_on_type(1 if lhs.val == rhs.val else 0) # type: ignore
			case Tk.AndAnd:
				return make_variant_based_on_type(
					1 if self.is_true(lhs) and self.is_true(rhs) else 0) # type: ignore
			case Tk.AndAnd:
				return make_variant_based_on_type(
					1 if self.is_true(lhs) or self.is_true(rhs) else 0) # type: ignore
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
			case Tk.LeftBracket:
				return lhs.val[rhs.val] # type: ignore
			case _:
				self.error(f"unknow operation {op}")

	#endregion

	#region Run Line

	def run(self, modify_frames = True):
		self.ptr = 0

		if len(self.tokens) == 0:
			return

		if modify_frames:
			self.frames.append({})

		while self.ptr < len(self.tokens):
			ignore_semi = False
			first = self.tokens[self.ptr]

			if first == Tk.Key_Let:
				name = self.expect_next_token(Tk.Id).val
				self.expect_next_token(Tk.Equal)
				tree = self.evaluate_next_to_tree()
				value = self.evaluate_tree(tree)

				self.create_frame_variable(name, value)

			elif first == Tk.Key_If:
				ignore_semi = True
				condition = self.evaluate_next_to_tree()
				
				true_body = self.next_block()
				false_body = []

				do_else = self.peek_or_useless()
				if do_else == Tk.Key_Else:
					self.next_token()
					false_body = self.next_block()
				
				condition = self.evaluate_tree(condition)
				condition = self.is_true(condition)

				if condition:
					sub_block = Block(true_body, self.frames)
					sub_block.run()
				elif do_else:
					sub_block = Block(false_body, self.frames)
					sub_block.run()

			elif first == Tk.Key_While:
				ignore_semi = True
				condition = self.evaluate_next_to_tree()
				
				body = self.next_block()
				sub_block = Block(body, self.frames)

				while self.is_true(self.evaluate_tree(condition)):
					sub_block.run()
			
			else:
				self.ptr -= 1
				tree = self.evaluate_next_to_tree()
				self.evaluate_tree(tree)

			# asserts semi colon
			if not ignore_semi:
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
			{"println": Extern(lambda x: print(str(x)), 1)},
			{"print": Extern(lambda x: print(str(x), end=""), 1)},
			{"true": Variant(Typ.Int, 1)},
			{"false": Variant(Typ.Int, 0)}
		]

		self.frames.append({})
		root_block = Block(self.tokens, self.frames)
		root_block.run(False)
