
import re
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
	
	Tk.NotAssigned: r"\S",
}


@dataclass
class Token:
	typ: Tk
	val: Any
	line: int
	col: int


class Lang:
	def __init__(self, src: str) -> None:
		self.src = src
		self.tokens = []


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

			tokens.append(Token(typ, val, line, col))

		self.tokens = tokens


	def run(self):
		print(self.tokens)
