
import lang

with open("test.txt", encoding="utf-8") as file:
	ctx = file.read()

lng = lang.Lang(ctx)
lng.parse()
lng.run()
