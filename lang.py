
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
	
	Tk.Id: r"[a-zA-Z_][a-zA-Z0-9_]*",
	Tk.Equal: r"=",
	Tk.Float: r"[+-]?[0-9]+\.[0-9]+", # order is important
	Tk.Int: r"[+-]?[0-9]+",
	Tk.Plus: r"\+",
	Tk.Star: r"\*",
	Tk.Semi: r";",
	
	Tk.NotAssigned: r"\S",
	Tk.Useless: r"\/\/[^\n]*",
}


@dataclass
class Token:
	typ: Tk
	val: Any


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

			tokens.append(Token(typ, val))

		self.tokens = tokens


	def run(self):
		print(self.tokens)
