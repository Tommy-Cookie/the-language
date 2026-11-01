
# ================
# batching scripts
# ================

from io import StringIO
from contextlib import redirect_stdout, redirect_stderr
from traceback import format_exc
import lang

with open("test.txt", encoding="utf-8") as file:
	ctx = file.read()


ls = ctx.split("==== NEXT TEST ====\n")
final = ""

for i, l in enumerate(ls, start=1):
	out = StringIO()
	err = StringIO()

	with redirect_stdout(out), redirect_stderr(err):
		lng = lang.Lang(l)
		error = False
		try:
			lng.parse()
			lng.run()
		except SystemExit:
			pass
		except Exception as e:
			final += f"==== TEST {i} RAISED AN INTERNEL ERROR ====\n"
			final += format_exc()
			final += f"==== END OF TEST {i} INTERNEL ERROR ====\n"
			final = final.replace("F:\\Python_second\\TheLanguage\\", "\\")
			error = True

	if error:
		continue

	final += f"==== BEGIN OF TEST {i} STDOUT ====\n"
	final += out.getvalue()
	final += f"\n==== END OF TEST {i} STDOUT ====\n"

	err_val = err.getvalue()
	if len(err_val) > 0:
		final += f"==== BEGIN OF TEST {i} STDERR ====\n"
		final += err_val
		final += f"\n==== END OF TEST {i} STDERR ====\n"

with open("result.txt", "w", encoding="utf-8") as file:
	file.write(final)
